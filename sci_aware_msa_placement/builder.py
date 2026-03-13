import random
from dataclasses import (
    dataclass,
    field,
)
from pathlib import Path

from swiplserver import PrologMQI

from sci_aware_msa_placement.models import (
    FactoryNode,
    Microservice,
    ModeEnv,
    NodeType,
)
from sci_aware_msa_placement.settings import (
    APP_DIR,
    CURATED_EXTRA_NODE_PAIR_SIZE,
    ENCODING,
    INFRA_DIR,
    MODE_FILE_PREFIX,
    OPTIMAL_KEYS,
    PL_SUFFIX,
    PROLOG,
)
from sci_aware_msa_placement.utils import application_path


@dataclass(slots=True)
class Builder:
    mode: ModeEnv
    n: int
    seed: int | None = None
    application_name: str | None = None
    infra_dir: Path = INFRA_DIR
    app_dir: Path = APP_DIR
    optimal: list[dict[str, str]] = field(default_factory=list)

    def build(self) -> Path:
        self._set_seed()
        self._reset_factory()
        if self.mode == ModeEnv.RANDOM:
            content = self._build_random()
            filename = self._make_filename(MODE_FILE_PREFIX["random"])
        elif self.mode == ModeEnv.CURATED:
            content = self._build_curated()
            filename = self._make_filename(MODE_FILE_PREFIX["curated"])
        else:
            raise ValueError(f"Invalid mode {self.mode}")

        return self._write_file(filename, content)

    def _set_seed(self) -> None:
        if self.seed is not None:
            random.seed(self.seed)

    def _reset_factory(self) -> None:
        FactoryNode.reset_num_nodes_s()
        FactoryNode.reset_num_nodes_t()

    def _make_filename(self, prefix: str) -> str:
        return f"{prefix}-{self.n}{PL_SUFFIX}"

    def _write_file(self, filename: str, content: str) -> Path:
        self.infra_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.infra_dir / filename
        output_path.write_text(content, encoding=ENCODING)
        return output_path

    def _serialize(self, nodes: list) -> str:
        node_facts = "".join(f"{node}\n" for node in nodes)
        carbon_intensity_facts = "".join(
            PROLOG["carbon_intensity_fact"].format(name=node.name, ci=node.ci)
            for node in nodes
        ).replace("'", "")
        return node_facts + carbon_intensity_facts

    def _build_random(self) -> str:
        nodes = [FactoryNode.node(NodeType.RANDOM) for _ in range(self.n)]
        return self._serialize(nodes)

    def _build_curated(self) -> str:
        microservices = self._load_microservices()

        if self.n < len(microservices):
            raise ValueError(
                f"Number of nodes ({self.n}) must be >= number of microservices ({len(microservices)})"
            )

        nodes = []
        extra_nodes = self.n - len(microservices)

        for _ in range(extra_nodes // CURATED_EXTRA_NODE_PAIR_SIZE):
            ms = random.choice(microservices)
            nodes.append(FactoryNode.node(NodeType.DIRTY, ms))
            nodes.append(FactoryNode.node(NodeType.BROKEN, ms))

        for ms in microservices:
            fit_node = FactoryNode.node(NodeType.FIT, ms)
            self.optimal.append(
                {
                    OPTIMAL_KEYS["microservice"]: ms.name,
                    OPTIMAL_KEYS["node"]: fit_node.name,
                }
            )
            nodes.append(fit_node)

        return self._serialize(nodes)

    def _load_microservices(self) -> list[Microservice]:
        app_path = application_path(self.app_dir, self.application_name)

        with PrologMQI() as mqi, mqi.create_thread() as prolog:
            prolog.query(f"consult('{app_path.as_posix()}').")
            result = prolog.query(PROLOG["application_query"])[0]
            ms_names = result["MS"]

            return [
                self._build_microservice(
                    ms_name,
                    prolog.query(PROLOG["microservice_query"].format(name=ms_name))[0],
                )
                for ms_name in ms_names
            ]

    def _build_microservice(self, name: str, data: dict) -> Microservice:
        return Microservice(
            name=name,
            ncpu=data["CPU"],
            ram=data["RAM"],
            bwin=data["BWIN"],
            bwout=data["BWOUT"],
            tir=data["TiR"],
        )
