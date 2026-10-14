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
        try:
            application_path, application, application_metadata = build_application(
                self.parameters, self.work_dir
            )
            infrastructure_path, infrastructure_metadata = build_network(
                self.parameters, self.work_dir
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
                time=None,
                component_operational_sci=None,
                component_embodied_sci=None,
                network_operational_sci=None,
                network_embodied_sci=None,
                nodes_used=None,
                placement=None,
            )
        except Exception as error:
            result.update(
                success=False,
                timeout=False,
                error=str(error),
                time=None,
                component_operational_sci=None,
                component_embodied_sci=None,
                network_operational_sci=None,
                network_embodied_sci=None,
                nodes_used=None,
                placement=None,
            )
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
                f"componentPlacementSCI({application},P,"
                "ComponentOperationalSCI,ComponentEmbodiedSCI),"
                f"networkSCI({application},P,NetworkOperationalSCI,"
                "NetworkEmbodiedSCI)."
            )
            prolog.query_async(query, find_all=False)
            raw_result = prolog.query_async_result()
        return self._normalize_result(parse_prolog(raw_result))

    def _normalize_result(self, result: Any) -> dict[str, Any]:
        if isinstance(result, list):
            result = result[0] if result else False
        if not isinstance(result, dict):
            return {
                "time": None,
                "component_operational_sci": None,
                "component_embodied_sci": None,
                "network_operational_sci": None,
                "network_embodied_sci": None,
                "nodes_used": None,
                "placement": None,
                "error": "No solution found",
            }
        return {
            "time": result.get("Time"),
            "component_operational_sci": result.get("ComponentOperationalSCI"),
            "component_embodied_sci": result.get("ComponentEmbodiedSCI"),
            "network_operational_sci": result.get("NetworkOperationalSCI"),
            "network_embodied_sci": result.get("NetworkEmbodiedSCI"),
            "nodes_used": result.get("N"),
            "placement": json.dumps(result.get("P"), separators=(",", ":")),
            "error": None,
        }
