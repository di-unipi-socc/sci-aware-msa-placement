from pathlib import Path

from ray import tune

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
RESULTS_DIR = PROJECT_ROOT / "results"
PARQUETS_DIR = RESULTS_DIR / "parquets"
PROLOG_DIR = PROJECT_ROOT / "prolog"
PLACEMENT_PL = PROLOG_DIR / "placement.pl"

# Execution
EXPERIMENT_NAME = "network-sci"
RAY_ADDRESS = "auto"
TIMEOUT_SECONDS = 1800
ENCODING = "utf-8"

# Experimental grid
SEEDS = [151195, 30997, 50296, 42, 21297]
APPLICATION_SIZES = [10, 20, 40]
APPLICATION_TOPOLOGIES = ["erdos_renyi", "barabasi_albert", "watts_strogatz"]
INFRASTRUCTURE_SIZES = [16, 32, 64]
INFRASTRUCTURE_TOPOLOGIES = ["erdos_renyi", "barabasi_albert", "watts_strogatz"]
TOP_K_VALUES = [1, 10, 100]
NETWORK_WEIGHTS = [(0.33, 0.33, 0.34), (0.50, 0.25, 0.25), (0.25, 0.25, 0.50)]
HEURISTICS = [
    *(f"capacityonly({k})" for k in TOP_K_VALUES),
    *(f"greenonly({k})" for k in TOP_K_VALUES),
    *(
        f"networkaware({alpha},{beta},{gamma})"
        for alpha, beta, gamma in NETWORK_WEIGHTS
    ),
    "scigreedy",
    "scilocalsearch",
]
SCOPES = ["components_only", "components_and_network"]
ROUTE_PROFILES = [
    {
        "name": "renater_montpellier_peak",
        "operational_per_gb": 0.000793,
        "embodied_per_gb": 0.000493,
    },
    {
        "name": "renater_montpellier_offpeak",
        "operational_per_gb": 0.001400,
        "embodied_per_gb": 0.000493,
    },
]
INCLUDE_NETWORK_EMBODIED = [False, True]

SEARCH_SPACE = {
    "seed": tune.grid_search(SEEDS),
    "application_size": tune.grid_search(APPLICATION_SIZES),
    "application_topology": tune.grid_search(APPLICATION_TOPOLOGIES),
    "infrastructure_size": tune.grid_search(INFRASTRUCTURE_SIZES),
    "infrastructure_topology": tune.grid_search(INFRASTRUCTURE_TOPOLOGIES),
    "heuristic": tune.grid_search(HEURISTICS),
    "scope": tune.grid_search(SCOPES),
    "route_profile": tune.grid_search(ROUTE_PROFILES),
    "include_network_embodied": False,  # tune.grid_search(INCLUDE_NETWORK_EMBODIED),
}

DEBUG_CONFIG = {
    "seed": 42,
    "application_size": 10,
    "application_topology": "erdos_renyi",
    "infrastructure_size": 16,
    "infrastructure_topology": "erdos_renyi",
    "heuristic": "networkaware(0.33,0.33,0.34)",
    "scope": "components_and_network",
    "route_profile": ROUTE_PROFILES[0],
    "include_network_embodied": False,
}

# Graph generation
ERDOS_RENYI_PROBABILITY = 0.20
BARABASI_ALBERT_ATTACHMENTS = 2
WATTS_STROGATZ_NEIGHBORS = 4
WATTS_STROGATZ_REWIRE_PROBABILITY = 0.15
ENDPOINT_COUNT = 6

# Synthetic application
CPU_REQUIREMENT_RANGE = (0.10, 1.00)
RAM_REQUIREMENT_RANGE = (0.25, 2.00)
BANDWIDTH_REQUIREMENT_RANGE = (0.01, 0.25)
TIME_IN_RESERVE_RANGE = (0.10, 1.00)
INTERACTION_GB_RANGE = (0.000005, 0.0005)
FUNCTIONAL_UNITS = 25_000_000

# Synthetic infrastructure
NODE_CPU_RANGE = (2, 16)
NODE_RAM_RANGE = (4.0, 32.0)
NODE_BANDWIDTH_RANGE = (1.0, 10.0)
POWER_PER_CPU_RANGE = (0.003, 0.010)
EXPECTED_LIFETIME_RANGE = (3.0, 7.0)
TOTAL_EMBODIED_EMISSIONS_RANGE = (100.0, 600.0)
PUE_RANGE = (1.05, 1.60)
CARBON_INTENSITY_RANGE = (0.03, 0.70)
LINK_DISTANCE_KM_RANGE = (20.0, 1200.0)
