from pathlib import Path

import ray
from ray import tune
from ray.tune import RunConfig

from sci_aware_msa_placement import config
from sci_aware_msa_placement.experiment import Experiment


def run_experiment(parameters: dict) -> dict:
    output_dir = Path(tune.get_context().get_trial_dir()) / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return Experiment(parameters, output_dir).run()


def main() -> None:
    if not ray.is_initialized():
        ray.init(address=config.RAY_ADDRESS)

    results = tune.Tuner(
        run_experiment,
        param_space=config.SEARCH_SPACE,
        run_config=RunConfig(
            name=config.EXPERIMENT_NAME,
            storage_path=str(config.OUTPUT_DIR),
        ),
    ).fit()

    output_dir = config.PARQUETS_DIR / config.EXPERIMENT_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "raw-sci-aware.parquet"
    results.get_dataframe().to_parquet(output_path, index=False)
    print(f"Results saved to {output_path}")


def debug_main() -> None:
    config.DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    print(Experiment(config.DEBUG_CONFIG, config.DEBUG_DIR).run())
