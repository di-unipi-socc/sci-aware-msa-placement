import argparse
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from data import ModeEnv, ModeTest
from settings import CURATED_CSV, RND_CSV

ENDPOINTS = list(range(1, 7))


def scalabilityResults(csvFile: str, modeTest: ModeTest, modeEnv: ModeEnv):
    """Plots the scalability results from a CSV file.

    Args:
        csvFile (str): Path to the CSV file containing the data.
        modeTest (Enum): Enum representing the test mode.
        modeEnv (Enum): Enum representing the environment mode. Can be either CRTD or RND.

    Raises:
        FileExistsError: If the CSV file is not found.
        ValueError: If an invalid modeEnv is provided.

    """
    try:
        df = pd.read_csv(csvFile)
    except:
        raise FileExistsError(f"\n\nFile {csvFile} not found\n")

    modetest = modeTest.name.lower()
    df.replace(["X", "/"], pd.NA, inplace=True)
    df[f"Time_{modetest}"] = pd.to_numeric(df[f"Time_{modetest}"], errors="coerce")

    df = df.dropna(subset=[f"Time_{modetest}"])

    avgTime = (
        df.groupby(["Microservices", "InfrastructureNodes"])[f"Time_{modetest}"]
        .mean()
        .reset_index()
    )

    plt.figure(figsize=(10, 6))
    if modeEnv == ModeEnv.CURATED:
        plt.plot(
            avgTime["InfrastructureNodes"],
            avgTime[f"Time_{modetest}"],
            marker="o",
            linestyle="-",
            label="6 Endpoints",
        )
    elif modeEnv == ModeEnv.RANDOM:
        for i, ms in enumerate(avgTime["Microservices"].unique()):
            ms_data = avgTime[avgTime["Microservices"] == ms]
            plt.plot(
                ms_data["InfrastructureNodes"],
                ms_data[f"Time_{modetest}"],
                marker="o",
                linestyle="-",
                label=f"Microservices {ms}",
            )
    else:
        raise ValueError("Invalid modeEnv")

    plt.xlabel("Nodes")
    plt.xscale("log", base=2)
    plt.ylabel("Time (seconds)")
    plt.legend()
    plt.grid(True)
    plt.show()


def accuracyResults(csvFile: str, modeTest: ModeTest, modeEnv: ModeEnv):
    """Plots the accuracy results from a CSV file.

    Args:
        csvFile (str): Path to the CSV file containing the data.
        modeTest (Enum): Enum representing the test mode.
        modeEnv (Enum): Enum representing the environment mode.

    Raises:
        FileExistsError: If the CSV file is not found.
        ValueError: If an invalid modeEnv is provided.

    """
    try:
        df = pd.read_csv(csvFile)
    except:
        raise FileExistsError(f"\n\nFile {csvFile} not found\n")

    modetest = modeTest.name.lower()
    df[f"SCI_{modetest}"] = pd.to_numeric(df[f"SCI_{modetest}"], errors="coerce")
    df["SCI_exhaustive"] = pd.to_numeric(df["SCI_exhaustive"], errors="coerce")
    df["InfrastructureNodes"] = pd.to_numeric(
        df["InfrastructureNodes"], errors="coerce"
    )
    df["Microservices"] = pd.to_numeric(df["Microservices"], errors="coerce")

    df = df.dropna(subset=[f"SCI_{modetest}"])

    avgSCI = (
        df.groupby(["Microservices", "InfrastructureNodes"])[f"SCI_{modetest}"]
        .mean()
        .reset_index()
    )
    avgSCIopt = (
        df.groupby(["Microservices", "InfrastructureNodes"])["SCI_exhaustive"]
        .mean()
        .reset_index()
    )
    mergedDF = pd.merge(
        avgSCI,
        avgSCIopt,
        on=["Microservices", "InfrastructureNodes"],
        suffixes=("", "_exhaustive"),
    )
    mergedDF["SCIDiff"] = (
        abs(mergedDF[f"SCI_{modetest}"] - mergedDF["SCI_exhaustive"])
        / mergedDF["SCI_exhaustive"]
    )

    plt.figure(figsize=(10, 6))
    if modeEnv == ModeEnv.CURATED:
        plt.plot(
            mergedDF["InfrastructureNodes"],
            mergedDF["SCIDiff"],
            marker="o",
            linestyle="-",
            label="6 Endpoints",
        )
    elif modeEnv == ModeEnv.RANDOM:
        for i, ms in enumerate(mergedDF["Microservices"].unique()):
            ms_data = mergedDF[mergedDF["Microservices"] == ms]
            plt.plot(
                ms_data["InfrastructureNodes"],
                ms_data["SCIDiff"],
                marker="o",
                linestyle="-",
                label=f"Microservices {ms}",
            )
    else:
        raise ValueError("Invalid modeEnv")

    plt.xlabel("Nodes")
    plt.ylabel("SCI Difference")
    plt.yscale("linear")
    plt.xscale("log", base=2)
    plt.ylim(bottom=0)
    plt.legend()
    plt.grid(True)
    plt.show()


prsr = argparse.ArgumentParser(description="Visualize the results of the experiments")
prsr.add_argument(
    "--modeEnv",
    type=str,
    choices=["random", "curated"],
    required=True,
    help="The mode of operation of the experiment that is to be visualized",
)
prsr.add_argument(
    "--modeTest",
    type=str,
    choices=["exhaustive", "greenonly", "capacityonly", "linearcombination"],
    required=True,
    help="The mode of the solution that is to be visualized",
)
prsr.add_argument(
    "--parameter",
    type=str,
    choices=["accuracy", "scalability"],
    required=True,
    help="The parameter that is to be visualized",
)
prsr.add_argument("--app", type=str, help="The application's name", required=True)
prsdArgs = prsr.parse_args()
mode = ModeEnv[prsdArgs.modeEnv.upper()]
test = ModeTest[prsdArgs.modeTest.upper()]
parameter = prsdArgs.parameter
CURATED_CSV = CURATED_CSV + prsdArgs.app + ".csv"
RND_CSV = RND_CSV + prsdArgs.app + ".csv"


if parameter == "accuracy":
    if mode == ModeEnv.CURATED:
        accuracyResults(CURATED_CSV, test, mode)
    elif mode == ModeEnv.RANDOM:
        accuracyResults(RND_CSV, test, mode)
    else:
        raise ValueError("Invalid modeEnv")
elif parameter == "scalability":
    if mode == ModeEnv.CURATED:
        scalabilityResults(CURATED_CSV, test, mode)
    elif mode == ModeEnv.RANDOM:
        scalabilityResults(RND_CSV, test, mode)
    else:
        raise ValueError("Invalid modeEnv")
