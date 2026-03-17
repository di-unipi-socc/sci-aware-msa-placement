from itertools import product

from ray.tune import grid_search

from sci_aware_msa_placement.models import ModeEnv, ModeTest


TIMEOUT = 900

APPLICATIONS = ["demo", "online-boutique"]

INFRASTRUCTURE_SIZES = [2**i for i in range(5, 21)]

SEEDS = [
    123457,
    654321,
    987652,
    567895,
    698081,
    123456,
    654321,
    987654,
    567890,
    698087,
]

COMMON_HEURISTICS = [
    ModeTest.GREENONLY,
    ModeTest.CAPACITYONLY,
    ModeTest.LINEARCOMBINATION,
]

MIN_CURATED_SIZE = {
    "demo": 6,
    "online-boutique": 10,
}
MODES = list(ModeEnv)


def get_heuristics(mode: ModeEnv) -> list[ModeTest]:
    if mode is ModeEnv.RANDOM:
        return [*COMMON_HEURISTICS, ModeTest.EXHAUSTIVE]

    if mode is ModeEnv.CURATED:
        return [*COMMON_HEURISTICS, ModeTest.BASE]

    raise ValueError(f"Invalid mode: {mode}")


def is_valid_config(application: str, mode: ModeEnv, infrastructure_size: int) -> bool:
    if mode is ModeEnv.CURATED:
        return infrastructure_size >= MIN_CURATED_SIZE[application]
    return True


def get_valid_configs() -> list[dict]:
    return [
        {
            "application": application,
            "mode": mode,
            "seed": seed,
            "infrastructure_size": infrastructure_size,
            "timeout": TIMEOUT,
            "heuristic": heuristic,
        }
        for application, mode, seed, infrastructure_size in product(
            APPLICATIONS,
            MODES,
            SEEDS,
            INFRASTRUCTURE_SIZES,
        )
        if is_valid_config(application, mode, infrastructure_size)
        for heuristic in get_heuristics(mode)
    ]


def get_search_space() -> dict:
    return {
        "experiment": grid_search(get_valid_configs()),
    }
