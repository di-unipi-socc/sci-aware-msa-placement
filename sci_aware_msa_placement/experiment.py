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
        result = self._base_result()
        try:
            application_path, application = build_application(
                self.parameters, self.work_dir
            )
            infrastructure_path = build_network(self.parameters, self.work_dir)
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
                nodes_used=None,
                placement=None,
            )
        return result

    def _base_result(self) -> dict[str, Any]:
        profile = self.parameters["route_profile"]
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
            "infrastructure_topology": self.parameters["infrastructure_topology"],
            "heuristic": self.parameters["heuristic"],
            "scope": self.parameters["scope"],
            "route_profile": profile["name"],
            "network_operational_per_gb": profile["operational_per_gb"],
            "network_embodied_per_gb": embodied_per_gb,
            "include_network_embodied": self.parameters[
                "include_network_embodied"
            ],
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
                f"{self.parameters['scope']},{application},P,SCI,N,Time)."
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
                "nodes_used": None,
                "placement": None,
                "error": "No solution found",
            }
        return {
            "time": result.get("Time"),
            "sci": result.get("SCI"),
            "nodes_used": result.get("N"),
            "placement": json.dumps(result.get("P"), separators=(",", ":")),
            "error": None,
        }
