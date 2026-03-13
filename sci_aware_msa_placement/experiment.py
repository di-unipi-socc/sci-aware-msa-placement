from dataclasses import dataclass
from pathlib import Path
from typing import Any

from swiplserver import (
    PrologMQI,
    PrologQueryTimeoutError,
)

from sci_aware_msa_placement.builder import Builder
from sci_aware_msa_placement.models import (
    ModeEnv,
    ModeTest,
)
from sci_aware_msa_placement.settings import (
    APP_DIR,
    INFRA_DIR,
    MAIN_PL,
    OPTIMAL_KEYS,
    PLACEMENT_ARITY,
    PROLOG,
    RESULT_KEYS,
    TIMEOUT,
)
from sci_aware_msa_placement.utils import application_path, parse_prolog


@dataclass(slots=True)
class Experiment:
    application_name: str
    infrastructure_size: int
    mode: ModeEnv
    heuristic: ModeTest
    infrastructure_dir: Path | None = INFRA_DIR
    seed: int | None = None
    app_dir: Path = APP_DIR
    timeout: int = TIMEOUT

    def run(self) -> dict[str, Any]:
        app_path = application_path(self.app_dir, self.application_name)
        self._validate_inputs(app_path)
        builder = Builder(
            mode=self.mode,
            n=self.infrastructure_size,
            seed=self.seed,
            infra_dir=self.infrastructure_dir,
            application_name=(
                self.application_name if self.mode == ModeEnv.CURATED else None
            ),
        )
        infra_path = builder.build()

        try:
            return {
                **self._base_result(),
                RESULT_KEYS["success"]: True,
                RESULT_KEYS["timeout"]: False,
                **self._run_prolog(builder, infra_path),
            }
        except PrologQueryTimeoutError:
            return {
                **self._base_result(),
                RESULT_KEYS["success"]: False,
                RESULT_KEYS["timeout"]: True,
                RESULT_KEYS["error"]: f"Query timed out after {self.timeout} seconds",
                RESULT_KEYS["time"]: None,
                RESULT_KEYS["sci"]: None,
                RESULT_KEYS["nodes_used"]: None,
                RESULT_KEYS["placement"]: None,
            }
        except Exception as exc:
            return {
                **self._base_result(infra_path),
                RESULT_KEYS["success"]: False,
                RESULT_KEYS["timeout"]: False,
                RESULT_KEYS["error"]: str(exc),
                RESULT_KEYS["time"]: None,
                RESULT_KEYS["sci"]: None,
                RESULT_KEYS["nodes_used"]: None,
                RESULT_KEYS["placement"]: None,
            }

    def _base_result(self) -> dict[str, Any]:
        return {
            RESULT_KEYS["application"]: self.application_name,
            RESULT_KEYS["mode"]: self.mode.name.lower(),
            RESULT_KEYS["heuristic"]: self.heuristic.name.lower(),
            RESULT_KEYS["seed"]: self.seed,
            RESULT_KEYS["size"]: self.infrastructure_size,
        }

    def _run_prolog(
        self,
        builder: Builder,
        infra_path: Path,
    ) -> dict[str, Any]:
        with (
            PrologMQI(query_timeout_seconds=self.timeout) as mqi,
            mqi.create_thread() as prolog,
        ):
            self._consult_files(prolog, infra_path)
            prolog.query_async(self._placement_query(builder), find_all=False)
            raw_result = prolog.query_async_result()
            print(raw_result)

        return self._normalize_result(parse_prolog(raw_result))

    def _consult_files(self, prolog, infra_path: Path) -> None:
        app_path = application_path(self.app_dir, self.application_name)
        prolog.query(f"consult('{app_path.as_posix()}').")
        prolog.query(f"consult('{infra_path.as_posix()}').")
        prolog.query(f"consult('{MAIN_PL.as_posix()}').")

    def _placement_query(self, builder: Builder) -> str:
        if self.heuristic == ModeTest.BASE:
            return PROLOG["timed_placement_base_query"].format(
                placement=self._placement_term(builder)
            )
        return PROLOG["timed_placement_query"].format(mode=self.heuristic.name.lower())

    def _placement_term(self, builder: Builder) -> str:
        if self.mode != ModeEnv.CURATED:
            raise ValueError("BASE heuristic requires curated mode")

        if not builder.optimal:
            raise ValueError("No placement available from curated builder")

        placement = [
            f"on({item[OPTIMAL_KEYS['microservice']]}, {item[OPTIMAL_KEYS['node']]})"
            for item in builder.optimal
        ]
        return f"[{', '.join(placement)}]"

    def _normalize_result(self, result: Any) -> dict[str, Any]:
        if isinstance(result, bool):
            return {
                RESULT_KEYS["time"]: None,
                RESULT_KEYS["sci"]: None,
                RESULT_KEYS["nodes_used"]: None,
                RESULT_KEYS["placement"]: None,
                RESULT_KEYS["error"]: "No solution found",
            }

        if isinstance(result, list):
            if not result:
                raise ValueError("Empty Prolog result")
            result = result[0]

        if not isinstance(result, dict):
            raise ValueError(f"Unexpected Prolog result: {result}")

        return {
            RESULT_KEYS["time"]: result.get("Time"),
            RESULT_KEYS["sci"]: result.get("SCI"),
            RESULT_KEYS["nodes_used"]: result.get("N"),
            RESULT_KEYS["placement"]: self._group_placement(result.get("P")),
        }

    def _group_placement(self, placement: Any) -> dict[str, list[str]] | None:
        if placement is None:
            return None

        grouped: dict[str, list[str]] = {}

        for item in placement:
            if (
                not isinstance(item, tuple)
                or len(item) != PLACEMENT_ARITY
                or item[0] != "on"
            ):
                raise ValueError(f"Invalid placement item: {item}")

            args = item[1]
            if not isinstance(args, (list, tuple)) or len(args) != PLACEMENT_ARITY:
                raise ValueError(f"Invalid placement args: {args}")

            microservice, node = str(args[0]), str(args[1])
            grouped.setdefault(node, []).append(microservice)

        return grouped

    def _validate_inputs(self, app_path: Path) -> None:
        if not app_path.exists():
            raise FileNotFoundError(f"Application file not found: {app_path}")

        if self.mode == ModeEnv.CURATED:
            microservice_count = self._count_microservices()
            if self.infrastructure_size < microservice_count:
                raise ValueError(
                    f"In curated mode, infrastructure_size ({self.infrastructure_size}) "
                    f"must be >= number of microservices ({microservice_count})"
                )

    def _count_microservices(self) -> int:
        with PrologMQI() as mqi, mqi.create_thread() as prolog:
            app_path = application_path(self.app_dir, self.application_name)
            prolog.query(f"consult('{app_path.as_posix()}').")
            result = prolog.query(PROLOG["count_microservices_query"])
        return int(result[0]["N"])
