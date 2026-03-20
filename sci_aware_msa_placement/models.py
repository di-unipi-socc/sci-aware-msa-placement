import random
from dataclasses import dataclass
from enum import IntEnum
from typing import ClassVar, Union


class NodeSize(IntEnum):
    NANO = 0
    MICRO = 1
    SMALL = 2
    MEDIUM = 3
    LARGE = 4
    XLARGE = 5
    X2LARGE = 6


class NodeType(IntEnum):
    RANDOM = 0
    FIT = 1
    BROKEN = 2
    DIRTY = 3


class ModeEnv(IntEnum):
    RANDOM = 0
    CURATED = 1


class ModeTest(IntEnum):
    EXHAUSTIVE = 0
    GREENONLY = 1
    CAPACITYONLY = 2
    LINEARCOMBINATION = 3
    BASE = 4


@dataclass(slots=True)
class Node:
    name: str
    ncpu: int
    ram: float
    bwin: float
    bwout: float
    e: float
    el: float
    te: float
    pue: float
    ci: float

    def __str__(self) -> str:
        return (
            f"node({self.name}, "
            f"tor({self.ncpu},{self.ram},{self.bwin},{self.bwout}), "
            f"{self.e}, {self.el}, {self.te}, {self.pue})."
        )


@dataclass(slots=True)
class Microservice:
    name: str
    ncpu: int
    ram: float
    bwin: float
    bwout: float
    tir: float

    def __str__(self) -> str:
        return (
            f"microservice({self.name}, "
            f"rr({self.ncpu},{self.ram},{self.bwin},{self.bwout}), {self.tir})."
        )


@dataclass(frozen=True, slots=True)
class NodeProfile:
    pue: float
    ci: float


class FactoryNode:
    num_nodes_s: ClassVar[list[int]] = [0] * len(NodeSize)
    num_nodes_t: ClassVar[list[int]] = [0] * len(NodeType)

    FIT_PROFILE: ClassVar[NodeProfile] = NodeProfile(pue=1.1, ci=0.1)
    CLEAN_PROFILE: ClassVar[NodeProfile] = NodeProfile(pue=1.05, ci=0.03)
    DIRTY_PROFILE: ClassVar[NodeProfile] = NodeProfile(pue=3.0, ci=1.1)

    SIZE_CONFIG: ClassVar[
        dict[NodeSize, dict[str, float | int | str | tuple[float, float]]]
    ] = {
        NodeSize.NANO: {
            "prefix": "n_",
            "ncpu": 2,
            "ram": 0.5,
            "bwin": 5,
            "bwout": 5,
            "e_range": (0.001, 0.005),
        },
        NodeSize.MICRO: {
            "prefix": "mi_",
            "ncpu": 2,
            "ram": 1,
            "bwin": 5,
            "bwout": 5,
            "e_range": (0.005, 0.01),
        },
        NodeSize.SMALL: {
            "prefix": "s_",
            "ncpu": 1,
            "ram": 1,
            "bwin": 3,
            "bwout": 3,
            "e_range": (0.01, 0.015),
        },
        NodeSize.MEDIUM: {
            "prefix": "m_",
            "ncpu": 2,
            "ram": 2,
            "bwin": 5,
            "bwout": 5,
            "e_range": (0.015, 0.025),
        },
        NodeSize.LARGE: {
            "prefix": "l_",
            "ncpu": 2,
            "ram": 8,
            "bwin": 12.5,
            "bwout": 12.5,
            "e_range": (0.025, 0.04),
        },
        NodeSize.XLARGE: {
            "prefix": "xl_",
            "ncpu": 4,
            "ram": 4,
            "bwin": 10,
            "bwout": 10,
            "e_range": (0.04, 0.06),
        },
        NodeSize.X2LARGE: {
            "prefix": "xl2_",
            "ncpu": 8,
            "ram": 32,
            "bwin": 15,
            "bwout": 15,
            "e_range": (0.06, 0.1),
        },
    }

    @classmethod
    def node(
        cls, node: Union[NodeSize, NodeType], ms: Microservice | None = None
    ) -> Node:
        if isinstance(node, NodeSize):
            return cls._node_by_size(node)
        if isinstance(node, NodeType):
            return cls._node_by_type(node, ms)
        raise ValueError("Invalid node type.")

    @classmethod
    def _random_node(cls) -> Node:
        random_size = NodeSize(random.randint(0, len(NodeSize) - 3))
        return cls.node(random_size)

    @classmethod
    def _node_by_type(cls, node_type: NodeType, ms: Microservice | None = None) -> Node:
        idx = cls.num_nodes_t[node_type.value]
        cls.num_nodes_t[node_type.value] += 1
        name_id = str(idx)

        if node_type is NodeType.RANDOM:
            return cls._random_node()

        if ms is None:
            raise ValueError("Microservice not provided.")

        if node_type is NodeType.FIT:
            # profile = cls.FIT_PROFILE
            return Node(
                name=f"f_{name_id}",
                ncpu=ms.ncpu,
                ram=ms.ram,
                bwin=ms.bwin,
                bwout=ms.bwout,
                e=random.uniform(0.15, 0.3),
                el=3,
                te=1500,
                pue=random.uniform(1.1, 1.2),
                ci=random.uniform(0.2, 0.5),
            )

        if node_type is NodeType.DIRTY:
            # profile = cls.DIRTY_PROFILE
            return Node(
                name=f"d_{name_id}",
                ncpu=ms.ncpu * random.randint(1, 2),
                ram=ms.ram * random.randint(1, 2),
                bwin=ms.bwin * random.randint(1, 2),
                bwout=ms.bwout * random.randint(1, 2),
                e=random.uniform(0.4, 0.6),
                el=2,
                te=2000,
                pue=random.uniform(2, 2.5),
                ci=random.uniform(0.5, 0.8),
            )

        if node_type is NodeType.BROKEN:
            # profile = cls.CLEAN_PROFILE
            specs = [ms.ncpu, ms.ram, ms.bwin, ms.bwout]
            specs[random.randint(0, len(specs) - 1)] = 0

            return Node(
                name=f"b_{name_id}",
                ncpu=specs[0],
                ram=specs[1],
                bwin=specs[2],
                bwout=specs[3],
                e=random.uniform(0.05, 0.1),
                el=7,
                te=1000,
                pue=random.uniform(1.05, 1.1),
                ci=random.uniform(0.03, 0.1),
            )

        raise ValueError("Invalid node type.")

    @classmethod
    def _node_by_size(cls, node_size: NodeSize) -> Node:
        cfg = cls.SIZE_CONFIG[node_size]
        idx = cls.num_nodes_s[node_size.value]
        cls.num_nodes_s[node_size.value] += 1

        e_min, e_max = cfg["e_range"]

        return Node(
            name=f"{cfg['prefix']}{idx}",
            ncpu=cfg["ncpu"],
            ram=cfg["ram"],
            bwin=cfg["bwin"],
            bwout=cfg["bwout"],
            e=random.uniform(e_min, e_max),
            el=random.randint(3, 7),
            te=random.randint(1000, 2000),
            pue=random.uniform(1.1, 3.0),
            ci=random.uniform(0.0097, 1.1),
        )

    @classmethod
    def reset_num_nodes_s(cls) -> None:
        cls.num_nodes_s = [0] * len(NodeSize)

    @classmethod
    def reset_num_nodes_t(cls) -> None:
        cls.num_nodes_t = [0] * len(NodeType)
