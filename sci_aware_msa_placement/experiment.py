import json
import math
from pathlib import Path
from typing import Any

from swiplserver import PrologMQI, PrologQueryTimeoutError

from sci_aware_msa_placement import config
from sci_aware_msa_placement.builder import build_application, build_network
from sci_aware_msa_placement.optimum import SOLVER_COLUMNS, solve_optimum
from sci_aware_msa_placement.utils import parse_prolog


class Experiment:
    def __init__(self, parameters: dict, work_dir: Path):
        self.parameters = parameters
        self.work_dir = work_dir

    def run(self) -> dict[str, Any]:
        result = dict.fromkeys(
            [
                "application_edges",
                "actual_endpoint_count",
                "average_interaction_gb",
                "expected_traffic_gb_per_invocation",
                "physical_links",
                "actual_mean_degree",
                "average_physical_link_distance_km",
                "average_route_distance_km",
                "maximum_route_distance_km",
                "time",
                "nodes_used",
                "placement",
                "component_operational_sci",
                "component_embodied_sci",
                "network_operational_sci",
                "network_embodied_sci",
                *SOLVER_COLUMNS,
            ]
        )
        result.update(success=False, timeout=False, error=None)
        try:
            app_path, application, app_metadata = build_application(
                self.parameters, self.work_dir
            )
            app_data = app_metadata.pop("_application_data")
            infra_path, infra_metadata = build_network(self.parameters, self.work_dir)
            network_data = infra_metadata.pop("_network_data")
            result.update(app_metadata)
            result.update(infra_metadata)
            placement, elapsed = None, None
            if self.parameters["heuristic"] == "optimum":
                placement, statistics = solve_optimum(
                    app_data, network_data, self.parameters
                )
                result.update(statistics)
                elapsed = (
                    statistics["solver_model_seconds"]
                    + statistics["solver_solve_seconds"]
                )
                result["time"] = elapsed
                if placement is None:
                    result["error"] = (
                        f"MILP did not certify an optimum: {statistics['solver_status']}"
                    )
                    return result
            metrics = self._run_prolog(
                application, app_path, infra_path, placement, elapsed
            )
            result.update(metrics)
            if result["solver_status"] == "optimal" and metrics["error"] is None:
                measured = (
                    metrics["component_operational_sci"]
                    + metrics["component_embodied_sci"]
                )
                if self.parameters["scope"] == "components_and_network":
                    measured += (
                        metrics["network_operational_sci"]
                        + metrics["network_embodied_sci"]
                    )
                if not math.isclose(
                    measured,
                    result["solver_objective_sci"],
                    rel_tol=config.MILP_VALIDATION_RTOL,
                    abs_tol=config.MILP_VALIDATION_ATOL,
                ):
                    raise ValueError(
                        f"MILP/Prolog SCI mismatch: {result['solver_objective_sci']} vs {measured}"
                    )
            result["success"] = metrics["error"] is None
        except PrologQueryTimeoutError:
            result.update(
                success=False,
                timeout=True,
                error=f"Prolog query timed out after {config.TIMEOUT_SECONDS} seconds",
            )
        except Exception as error:
            result.update(success=False, error=str(error))
        return result

    def _run_prolog(
        self, application, app_path, infra_path, placement=None, elapsed=None
    ):
        timeout = (
            None
            if self.parameters["heuristic"] == "optimum"
            else config.TIMEOUT_SECONDS
        )
        with (
            PrologMQI(query_timeout_seconds=timeout) as mqi,
            mqi.create_thread() as prolog,
        ):
            for path in (config.PLACEMENT_PL, app_path, infra_path):
                prolog.query(f"consult('{path.as_posix()}').")
            if placement is None:
                prefix = (
                    f"timedPlacement({self.parameters['heuristic']},"
                    f"{self.parameters['scope']},{application},P,_,N,Time),"
                )
            else:
                atoms = ",".join(f"on({m},{n})" for m, n in placement)
                prefix = (
                    f"P=[{atoms}],Time={elapsed!r},involvedNodes(P,N),"
                    "forall(member(on(M,Node),P),(microservice(M,RR,_),"
                    "select(on(M,Node),P,Rest),placementNode(Node,Rest,RR))),"
                )
            query = (
                prefix
                + f"componentPlacementSCI({application},P,ComponentOperationalSCI,ComponentEmbodiedSCI),"
                f"networkSCI({application},P,NetworkOperationalSCI,NetworkEmbodiedSCI)"
            )
            prolog.query_async(f"once(({query})).", find_all=False)
            raw = parse_prolog(prolog.query_async_result())
        if isinstance(raw, list):
            raw = raw[0] if raw else False
        if not isinstance(raw, dict):
            return {"error": "No eligible solution found"}
        return {
            "time": raw["Time"],
            "nodes_used": raw["N"],
            "placement": json.dumps(raw["P"], separators=(",", ":")),
            "component_operational_sci": raw["ComponentOperationalSCI"],
            "component_embodied_sci": raw["ComponentEmbodiedSCI"],
            "network_operational_sci": raw["NetworkOperationalSCI"],
            "network_embodied_sci": raw["NetworkEmbodiedSCI"],
            "error": None,
        }
