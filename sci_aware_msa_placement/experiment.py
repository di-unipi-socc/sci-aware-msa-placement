import json
from pathlib import Path
from typing import Any

from swiplserver import PrologMQI, PrologQueryTimeoutError

from sci_aware_msa_placement import config
from sci_aware_msa_placement.builder import build_application, build_network
from sci_aware_msa_placement.utils import parse_prolog


class Experiment:
    def __init__(self, parameters: dict, work_dir: Path):
        self.parameters = parameters
        self.work_dir = work_dir

    def run(self) -> dict[str, Any]:
        result = {
            "application_edges": None,
            "actual_endpoint_count": None,
            "average_interaction_gb": None,
            "expected_traffic_gb_per_invocation": None,
            "physical_links": None,
            "actual_mean_degree": None,
            "average_physical_link_distance_km": None,
            "average_route_distance_km": None,
            "maximum_route_distance_km": None,
        }
        result.update(self._empty_placement_result())
        try:
            application_path, application, application_metadata = build_application(
                self.parameters, self.work_dir
            )
            service_requirements = application_metadata.pop(
                "_service_requirements"
            )
            infrastructure_path, infrastructure_metadata = build_network(
                self.parameters,
                self.work_dir,
                application,
                service_requirements,
            )
            result.update(application_metadata)
            result.update(infrastructure_metadata)
            prolog_result = self._run_prolog(
                application, application_path, infrastructure_path
            )
            result.update(
                success=prolog_result["error"] is None,
                timeout=False,
                **prolog_result,
            )
        except PrologQueryTimeoutError:
            result.update(
                success=False,
                timeout=True,
                error=f"Query timed out after {config.TIMEOUT_SECONDS} seconds",
            )
        except Exception as error:
            result.update(success=False, timeout=False, error=str(error))
        return result

    def _run_prolog(
        self,
        application: str,
        application_path: Path,
        infrastructure_path: Path,
    ) -> dict[str, Any]:
        with (
            PrologMQI(query_timeout_seconds=config.TIMEOUT_SECONDS) as mqi,
            mqi.create_thread() as prolog,
        ):
            for path in (
                config.PLACEMENT_PL,
                application_path,
                infrastructure_path,
            ):
                prolog.query(f"consult('{path.as_posix()}').")
            query = (
                f"timedPlacement({self.parameters['heuristic']},"
                f"{self.parameters['scope']},{application},P,_,N,Time),"
                f"controlledPlacement({application},OptimalP),"
                f"componentPlacementSCI({application},P,"
                "ComponentOperationalSCI,ComponentEmbodiedSCI),"
                f"networkSCI({application},P,NetworkOperationalSCI,"
                "NetworkEmbodiedSCI),"
                f"componentPlacementSCI({application},OptimalP,"
                "OptimalComponentOperationalSCI,"
                "OptimalComponentEmbodiedSCI),"
                f"networkSCI({application},OptimalP,"
                "OptimalNetworkOperationalSCI,OptimalNetworkEmbodiedSCI)."
            )
            prolog.query_async(query, find_all=False)
            raw_result = prolog.query_async_result()
        return self._normalize_result(parse_prolog(raw_result))

    def _normalize_result(self, result: Any) -> dict[str, Any]:
        if isinstance(result, list):
            result = result[0] if result else False
        if not isinstance(result, dict):
            return {
                **self._empty_placement_result(),
                "error": "No solution found",
            }

        component_operational = result.get("OptimalComponentOperationalSCI")
        component_embodied = result.get("OptimalComponentEmbodiedSCI")
        network_operational = result.get("OptimalNetworkOperationalSCI")
        network_embodied = result.get("OptimalNetworkEmbodiedSCI")
        components_only_sci = component_operational + component_embodied
        components_and_network_sci = sum(
            (
                component_operational,
                component_embodied,
                network_operational,
                network_embodied,
            )
        )
        optimal_sci = (
            components_and_network_sci
            if self.parameters["scope"] == "components_and_network"
            else components_only_sci
        )
        return {
            "time": result.get("Time"),
            "component_operational_sci": result.get("ComponentOperationalSCI"),
            "component_embodied_sci": result.get("ComponentEmbodiedSCI"),
            "network_operational_sci": result.get("NetworkOperationalSCI"),
            "network_embodied_sci": result.get("NetworkEmbodiedSCI"),
            "optimal_component_operational_sci": component_operational,
            "optimal_component_embodied_sci": component_embodied,
            "optimal_network_operational_sci": network_operational,
            "optimal_network_embodied_sci": network_embodied,
            "optimal_components_only_sci": components_only_sci,
            "optimal_components_and_network_sci": components_and_network_sci,
            "optimal_sci": optimal_sci,
            "optimal_placement": json.dumps(
                result.get("OptimalP"), separators=(",", ":")
            ),
            "nodes_used": result.get("N"),
            "placement": json.dumps(result.get("P"), separators=(",", ":")),
            "error": None,
        }

    @staticmethod
    def _empty_placement_result() -> dict[str, Any]:
        return {
            "success": False,
            "timeout": False,
            "error": None,
            "time": None,
            "component_operational_sci": None,
            "component_embodied_sci": None,
            "network_operational_sci": None,
            "network_embodied_sci": None,
            "optimal_component_operational_sci": None,
            "optimal_component_embodied_sci": None,
            "optimal_network_operational_sci": None,
            "optimal_network_embodied_sci": None,
            "optimal_components_only_sci": None,
            "optimal_components_and_network_sci": None,
            "optimal_sci": None,
            "optimal_placement": None,
            "nodes_used": None,
            "placement": None,
        }
