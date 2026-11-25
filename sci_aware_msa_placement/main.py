from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import ray
from ray import tune
from ray.tune import RunConfig

from sci_aware_msa_placement import config
from sci_aware_msa_placement.experiment import Experiment
from sci_aware_msa_placement.optimum import SOLVER_COLUMNS


CONFIG_COLUMNS = {
    "config/scenario/seed": "seed",
    "config/scenario/application/size": "application_size",
    "config/scenario/application/topology": "application_topology",
    "config/scenario/infrastructure_size": "infrastructure_size",
    "config/scenario/infrastructure_graph/topology": "infrastructure_topology",
    "config/scenario/infrastructure_graph/density": "infrastructure_density",
    "config/placement/heuristic": "heuristic",
    "config/placement/scope": "scope",
    "config/route_profile/name": "route_profile",
    "config/route_profile/operational_per_gb": "network_operational_per_gb",
    "config/route_profile/embodied_per_gb": "network_embodied_per_gb",
    "config/include_network_embodied": "include_network_embodied",
}
STATISTIC_COLUMNS = [
    "application_edges",
    "actual_endpoint_count",
    "average_interaction_gb",
    "expected_traffic_gb_per_invocation",
    "physical_links",
    "actual_mean_degree",
    "average_physical_link_distance_km",
    "average_route_distance_km",
    "maximum_route_distance_km",
]
EXECUTION_COLUMNS = ["success", "timeout", "time", "nodes_used", "placement", "error"]
SCI_COLUMNS = [
    "component_operational_sci",
    "component_embodied_sci",
    "network_operational_sci",
    "network_embodied_sci",
]


def run_experiment(parameters: dict) -> dict:
    experiment_parameters = {
        **parameters["scenario"],
        **parameters["placement"],
        **{
            key: value
            for key, value in parameters.items()
            if key not in {"scenario", "placement"}
        },
    }
    with TemporaryDirectory(prefix="sci-aware-") as directory:
        return Experiment(experiment_parameters, Path(directory)).run()


def heuristic_parameters(heuristic: str) -> dict:
    parameters = {
        "heuristic_name": heuristic,
        "top_k": None,
        "green_weight": None,
        "capacity_weight": None,
        "centrality_weight": None,
    }
    if "(" not in heuristic:
        return parameters

    name, raw_arguments = heuristic[:-1].split("(", maxsplit=1)
    arguments = raw_arguments.split(",")
    parameters["heuristic_name"] = name
    if name in {"capacityonly", "greenonly"}:
        parameters["top_k"] = int(arguments[0])
    else:
        (
            parameters["green_weight"],
            parameters["capacity_weight"],
            parameters["centrality_weight"],
        ) = map(float, arguments)
    return parameters


def prepare_results(dataframe: pd.DataFrame) -> pd.DataFrame:
    configuration = dataframe[list(CONFIG_COLUMNS)].rename(columns=CONFIG_COLUMNS)
    heuristic_data = pd.DataFrame(
        configuration["heuristic"].map(heuristic_parameters).tolist(),
        index=dataframe.index,
    )
    measured = dataframe.reindex(
        columns=[*STATISTIC_COLUMNS, *EXECUTION_COLUMNS, *SCI_COLUMNS, *SOLVER_COLUMNS]
    )
    results = pd.concat([configuration, heuristic_data, measured], axis=1)
    return attach_optima(results)


def attach_optima(results: pd.DataFrame) -> pd.DataFrame:
    results = results.copy()
    results[SCI_COLUMNS] = results[SCI_COLUMNS].apply(pd.to_numeric, errors="raise")
    results["component_sci"] = (
        results["component_operational_sci"] + results["component_embodied_sci"]
    )
    results["network_sci"] = (
        results["network_operational_sci"] + results["network_embodied_sci"]
    )
    results["objective_sci"] = results["component_sci"] + np.where(
        results["scope"] == "components_and_network", results["network_sci"], 0
    )
    keys = [column for column in CONFIG_COLUMNS.values() if column != "heuristic"]
    references = results.loc[
        (results["heuristic"] == "optimum")
        & results["success"]
        & (results["solver_status"] == "optimal")
    ]
    reference_columns = [*SCI_COLUMNS, "objective_sci", "placement"]
    renamed = {column: f"optimal_{column}" for column in SCI_COLUMNS}
    renamed.update(objective_sci="optimal_sci", placement="optimal_placement")
    results = results.merge(
        references[keys + reference_columns].rename(columns=renamed),
        on=keys,
        how="left",
        validate="many_to_one",
    )
    # The two scopes generally have different optimal placements.
    instance_keys = [key for key in keys if key != "scope"]
    for scope in config.SCOPES:
        column = f"optimal_{scope}_sci"
        scoped = references.loc[
            references["scope"] == scope, [*instance_keys, "objective_sci"]
        ]
        results = results.merge(
            scoped.rename(columns={"objective_sci": column}),
            on=instance_keys,
            how="left",
            validate="many_to_one",
        )
    same = np.isclose(
        results["objective_sci"],
        results["optimal_sci"],
        rtol=config.MILP_VALIDATION_RTOL,
        atol=config.MILP_VALIDATION_ATOL,
    )
    if (
        (results["objective_sci"] < results["optimal_sci"]) & ~same & results["success"]
    ).any():
        raise ValueError("A heuristic SCI is below its certified optimum")
    results["optimality_ratio"] = results["objective_sci"] / results["optimal_sci"]
    results.loc[same, "optimality_ratio"] = 1.0
    results["optimality_gap_pct"] = 100 * (results["optimality_ratio"] - 1)
    results["absolute_gap_sci"] = results["objective_sci"] - results["optimal_sci"]
    results.loc[same, "absolute_gap_sci"] = 0.0
    return results


def build_tuner() -> tune.Tuner:
    experiment_path = config.OUTPUT_DIR / config.EXPERIMENT_NAME
    if config.RESUME_EXPERIMENT and tune.Tuner.can_restore(str(experiment_path)):
        return tune.Tuner.restore(
            str(experiment_path),
            trainable=run_experiment,
            resume_unfinished=config.RESUME_UNFINISHED_TRIALS,
            resume_errored=config.RESUME_ERRORED_TRIALS,
            restart_errored=config.RESTART_ERRORED_TRIALS,
        )
    return tune.Tuner(
        run_experiment,
        param_space=config.SEARCH_SPACE,
        run_config=RunConfig(
            name=config.EXPERIMENT_NAME,
            storage_path=str(config.OUTPUT_DIR),
        ),
    )


def main() -> None:
    if not ray.is_initialized():
        ray.init(address=config.RAY_ADDRESS)

    results = build_tuner().fit()

    output_dir = config.PARQUETS_DIR / config.EXPERIMENT_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "raw-sci-aware.parquet"
    prepare_results(results.get_dataframe()).to_parquet(output_path, index=False)
    print(f"Results saved to {output_path}")


def debug_main() -> None:
    config.DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    print(Experiment(config.DEBUG_CONFIG, config.DEBUG_DIR).run())
