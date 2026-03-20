import time
from pathlib import Path
from tempfile import TemporaryDirectory

import ray
from ray import tune
from ray.air import RunConfig

from sci_aware_msa_placement.experiment import Experiment
from sci_aware_msa_placement.models import (
    ModeEnv,
    ModeTest,
)
from sci_aware_msa_placement.search_space import get_search_space
from sci_aware_msa_placement.settings import (
    EXPERIMENT_NAME,
    OUTPUT_DIR,
    PARQUETS_DIR,
)


def sci_aware(config: dict) -> dict:
    cfg = config["experiment"]

    with TemporaryDirectory() as temp_dir:
        experiment = Experiment(
            application_name=cfg["application"],
            infrastructure_size=cfg["infrastructure_size"],
            mode=cfg["mode"],
            heuristic=cfg["heuristic"],
            infrastructure_dir=Path(temp_dir),
            seed=cfg["seed"],
            timeout=cfg["timeout"],
        )

        return experiment.run()


def main() -> Path:
    start_time = time.time()
    if not ray.is_initialized():
        ray.init(address="auto")

    tuner = tune.Tuner(
        sci_aware,
        param_space=get_search_space(),
        run_config=RunConfig(
            name=EXPERIMENT_NAME,
            storage_path=str(OUTPUT_DIR),
        ),
    )

    results = tuner.fit()
    dataframe = results.get_dataframe()

    output_path = PARQUETS_DIR / EXPERIMENT_NAME
    output_path.mkdir(parents=True, exist_ok=True)
    output_path = output_path / "raw-sci-aware.parquet"

    dataframe.to_parquet(output_path, index=False)
    print(f"Saved results to: {output_path}")
    print(f"Total execution time: {time.time() - start_time:.4f} seconds")


def debug_main():
    for h in [ModeTest.GREENONLY, ModeTest.CAPACITYONLY, ModeTest.LINEARCOMBINATION]:
        result = sci_aware(
            {
                "experiment": {
                    "application": "online-boutique",
                    "infrastructure_size": 2**20,
                    "mode": ModeEnv.CURATED,
                    "heuristic": h,
                    "seed": 42,
                    "timeout": 600,
                }
            }
        )
        print(result)
