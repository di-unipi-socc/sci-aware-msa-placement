import json
from pathlib import Path
from typing import Any

from swiplserver import PrologMQI, PrologQueryTimeoutError

from sci_aware_msa_placement import config
from sci_aware_msa_placement.builder import (
    build_application,
    build_network,
    node_profile_counts,
)
from sci_aware_msa_placement.utils import parse_prolog


class Experiment:
    def __init__(self, parameters: dict, work_dir: Path):
        self.parameters = parameters
        self.work_dir = work_dir

    def run(self) -> dict[str, Any]:
        result = self._base_result()
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
                sci=None,
                objective_sci=None,
                total_sci=None,
                component_sci=None,
                component_operational_sci=None,
                component_embodied_sci=None,
                network_sci=None,
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
                sci=None,
                objective_sci=None,
                total_sci=None,
                component_sci=None,
                component_operational_sci=None,
                component_embodied_sci=None,
                network_sci=None,
                network_operational_sci=None,
                network_embodied_sci=None,
                nodes_used=None,
                placement=None,
            )
        return result

    def _base_result(self) -> dict[str, Any]:
        profile = self.parameters["route_profile"]
        graph = self.parameters["infrastructure_graph"]
        heuristic = self._heuristic_parameters()
        profile_counts = node_profile_counts(self.parameters["infrastructure_size"])
        embodied_per_gb = (
            profile["embodied_per_gb"]
            if self.parameters["include_network_embodied"]
            else 0.0
        )
        return {
            "seed": self.parameters["seed"],
            "application_size": self.parameters["application_size"],
            "application_topology": self.parameters["application_topology"],
            "infrastructure_size": self.parameters["infrastructure_size"],
            "infrastructure_topology": graph["topology"],
            "infrastructure_density": graph["density"],
            "heuristic": self.parameters["heuristic"],
            **heuristic,
            "scope": self.parameters["scope"],
            "route_profile": profile["name"],
            "network_operational_per_gb": profile["operational_per_gb"],
            "network_embodied_per_gb": embodied_per_gb,
            "include_network_embodied": self.parameters["include_network_embodied"],
            "target_mean_degree": config.AVERAGE_DEGREE_BY_DENSITY[graph["density"]],
            "functional_units": config.FUNCTIONAL_UNITS,
            "endpoint_count": config.ENDPOINT_COUNT,
            "cpu_requirement_min": config.CPU_REQUIREMENT_RANGE[0],
            "cpu_requirement_max": config.CPU_REQUIREMENT_RANGE[1],
            "ram_requirement_min": config.RAM_REQUIREMENT_RANGE[0],
            "ram_requirement_max": config.RAM_REQUIREMENT_RANGE[1],
            "bandwidth_requirement_min": config.BANDWIDTH_REQUIREMENT_RANGE[0],
            "bandwidth_requirement_max": config.BANDWIDTH_REQUIREMENT_RANGE[1],
            "time_in_reserve_min": config.TIME_IN_RESERVE_RANGE[0],
            "time_in_reserve_max": config.TIME_IN_RESERVE_RANGE[1],
            "interaction_gb_min": config.INTERACTION_GB_RANGE[0],
            "interaction_gb_max": config.INTERACTION_GB_RANGE[1],
            "application_er_probability": config.ERDOS_RENYI_PROBABILITY,
            "application_ba_attachments": config.BARABASI_ALBERT_ATTACHMENTS,
            "application_ws_neighbors": config.WATTS_STROGATZ_NEIGHBORS,
            "application_ws_rewire_probability": (
                config.WATTS_STROGATZ_REWIRE_PROBABILITY
            ),
            "link_distance_km_min": config.LINK_DISTANCE_KM_RANGE[0],
            "link_distance_km_max": config.LINK_DISTANCE_KM_RANGE[1],
            "network_reference_distance_km": 700,
            "expected_lifetime_min": config.EXPECTED_LIFETIME_RANGE[0],
            "expected_lifetime_max": config.EXPECTED_LIFETIME_RANGE[1],
            "pue_min": config.PUE_RANGE[0],
            "pue_max": config.PUE_RANGE[1],
            "carbon_intensity_min": config.CARBON_INTENSITY_RANGE[0],
            "carbon_intensity_max": config.CARBON_INTENSITY_RANGE[1],
            "fix_topology_density": config.FIX_TOPOLOGY_DENSITY,
            "timeout_seconds": config.TIMEOUT_SECONDS,
            "node_resource_profiles": json.dumps(
                config.NODE_RESOURCE_PROFILES, separators=(",", ":")
            ),
            "application_edges": None,
            "actual_endpoint_count": None,
            "average_interaction_gb": None,
            "expected_traffic_gb_per_invocation": None,
            "physical_links": None,
            "actual_mean_degree": None,
            "average_physical_link_distance_km": None,
            "average_route_distance_km": None,
            "maximum_route_distance_km": None,
            **{f"{name}_nodes": count for name, count in profile_counts.items()},
        }

    def _heuristic_parameters(self) -> dict[str, Any]:
        heuristic = self.parameters["heuristic"]
        if "(" not in heuristic:
            return {
                "heuristic_name": heuristic,
                "top_k": None,
                "green_weight": None,
                "capacity_weight": None,
                "centrality_weight": None,
            }

        name, raw_arguments = heuristic[:-1].split("(", maxsplit=1)
        arguments = raw_arguments.split(",")
        if name in {"capacityonly", "greenonly"}:
            return {
                "heuristic_name": name,
                "top_k": int(arguments[0]),
                "green_weight": None,
                "capacity_weight": None,
                "centrality_weight": None,
            }

        alpha, beta, gamma = map(float, arguments)
        return {
            "heuristic_name": name,
            "top_k": None,
            "green_weight": alpha,
            "capacity_weight": beta,
            "centrality_weight": gamma,
        }

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
                f"{self.parameters['scope']},{application},P,SCI,N,Time),"
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
                "sci": None,
                "objective_sci": None,
                "total_sci": None,
                "component_sci": None,
                "component_operational_sci": None,
                "component_embodied_sci": None,
                "network_sci": None,
                "network_operational_sci": None,
                "network_embodied_sci": None,
                "nodes_used": None,
                "placement": None,
                "error": "No solution found",
            }
        component_operational_sci = result.get("ComponentOperationalSCI")
        component_embodied_sci = result.get("ComponentEmbodiedSCI")
        network_operational_sci = result.get("NetworkOperationalSCI")
        network_embodied_sci = result.get("NetworkEmbodiedSCI")
        component_sci = component_operational_sci + component_embodied_sci
        network_sci = network_operational_sci + network_embodied_sci
        objective_sci = result.get("SCI")
        return {
            "time": result.get("Time"),
            "sci": objective_sci,
            "objective_sci": objective_sci,
            "total_sci": component_sci + network_sci,
            "component_sci": component_sci,
            "component_operational_sci": component_operational_sci,
            "component_embodied_sci": component_embodied_sci,
            "network_sci": network_sci,
            "network_operational_sci": network_operational_sci,
            "network_embodied_sci": network_embodied_sci,
            "nodes_used": result.get("N"),
            "placement": json.dumps(result.get("P"), separators=(",", ":")),
            "error": None,
        }
