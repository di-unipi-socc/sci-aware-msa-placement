from pathlib import Path
from tempfile import TemporaryDirectory

import ray
from ray import tune
from ray.air import RunConfig

from sci_aware_msa_placement import config
from sci_aware_msa_placement.experiment import Experiment


def run_experiment(parameters: dict) -> dict:
    with TemporaryDirectory() as work_dir:
        return Experiment(parameters, Path(work_dir)).run()


def main() -> Path:
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
    return output_path


def debug_main() -> dict:
    result = run_experiment(config.DEBUG_CONFIG)
    print(result)
    return result
