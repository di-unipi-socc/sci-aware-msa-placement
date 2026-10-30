from pathlib import Path

from ray import tune

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DEBUG_DIR = PROJECT_ROOT / "debug-dir"
RESULTS_DIR = PROJECT_ROOT / "results"
PARQUETS_DIR = RESULTS_DIR / "parquets"
PROLOG_DIR = PROJECT_ROOT / "prolog"
PLACEMENT_PL = PROLOG_DIR / "placement.pl"

# Execution
EXPERIMENT_NAME = "network-sci-controlled"
RAY_ADDRESS = "auto"
TIMEOUT_SECONDS = 1800
ENCODING = "utf-8"
RESUME_EXPERIMENT = True
RESUME_UNFINISHED_TRIALS = True
RESUME_ERRORED_TRIALS = False
RESTART_ERRORED_TRIALS = True

# Experimental grid
SEEDS = [151195, 30997, 50296, 42, 21297]
SYNTHETIC_APPLICATION_SIZES = [10, 20, 40]
SYNTHETIC_APPLICATION_TOPOLOGIES = ["erdos_renyi", "barabasi_albert"]
APPLICATIONS = [
    {"topology": topology, "size": size}
    for topology in SYNTHETIC_APPLICATION_TOPOLOGIES
    for size in SYNTHETIC_APPLICATION_SIZES
] + [{"topology": "online_boutique", "size": 10}]
INFRASTRUCTURE_SIZES = [16, 32, 64, 128, 256, 512]
INFRASTRUCTURE_TOPOLOGIES = [
    "erdos_renyi",
    "barabasi_albert",
    "internet_as_graph",
]
INFRASTRUCTURE_DENSITIES = ["sparse", "medium", "dense"]
TOP_K_VALUES = [1, 100, 1000]
NETWORK_WEIGHTS = [
    (0.33, 0.33, 0.34),
    (0.60, 0.20, 0.20),
    (0.20, 0.60, 0.20),
    (0.20, 0.20, 0.60),
]
HEURISTICS = [
    "controlled",
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
SCOPE_DEPENDENT_HEURISTICS = {"controlled", "scigreedy", "scilocalsearch"}
PLACEMENT_CONFIGS = [
    {"heuristic": heuristic, "scope": scope}
    for heuristic in HEURISTICS
    for scope in (
        SCOPES
        if heuristic in SCOPE_DEPENDENT_HEURISTICS
        else ["components_and_network"]
    )
]
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
INCLUDE_NETWORK_EMBODIED = False
FIX_TOPOLOGY_DENSITY = True

FIXED_INFRASTRUCTURE_GRAPHS = [
    {"topology": "erdos_renyi", "density": "dense"},
    {"topology": "barabasi_albert", "density": "medium"},
    {"topology": "internet_as_graph", "density": "sparse"},
]
VARIABLE_INFRASTRUCTURE_GRAPHS = [
    {"topology": topology, "density": density}
    for topology in INFRASTRUCTURE_TOPOLOGIES
    for density in INFRASTRUCTURE_DENSITIES
]
INFRASTRUCTURE_GRAPHS = (
    FIXED_INFRASTRUCTURE_GRAPHS
    if FIX_TOPOLOGY_DENSITY
    else VARIABLE_INFRASTRUCTURE_GRAPHS
)

SCENARIOS = [
    {
        "seed": seed,
        "application": application,
        "infrastructure_size": infrastructure_size,
        "infrastructure_graph": infrastructure_graph,
    }
    for seed in SEEDS
    for application in APPLICATIONS
    for infrastructure_size in INFRASTRUCTURE_SIZES
    for infrastructure_graph in INFRASTRUCTURE_GRAPHS
    if infrastructure_size >= application["size"] + 2
]

SEARCH_SPACE = {
    "scenario": tune.grid_search(SCENARIOS),
    "placement": tune.grid_search(PLACEMENT_CONFIGS),
    "route_profile": tune.grid_search(ROUTE_PROFILES),
    "include_network_embodied": INCLUDE_NETWORK_EMBODIED,
}

DEBUG_CONFIG = {
    "seed": 42,
    "application": APPLICATIONS[0],
    "infrastructure_size": 16,
    "infrastructure_graph": FIXED_INFRASTRUCTURE_GRAPHS[0],
    "heuristic": "networkaware(0.33,0.33,0.34)",
    "scope": "components_and_network",
    "route_profile": ROUTE_PROFILES[0],
    "include_network_embodied": INCLUDE_NETWORK_EMBODIED,
}

# Graph generation
MIN_GRAPH_SIZE = 2
ERDOS_RENYI_PROBABILITY = 0.20
BARABASI_ALBERT_ATTACHMENTS = 2
AVERAGE_DEGREE_BY_DENSITY = {
    "sparse": 2,
    "medium": 4,
    "dense": 8,
}
ENDPOINT_COUNT = 6
ONLINE_BOUTIQUE_PATH = (
    PROJECT_ROOT
    / "data"
    / "applications"
    / "online-boutique"
    / "applicationFULLms-realistic.pl"
)

# Synthetic application
CPU_REQUIREMENT_RANGE = (0.25, 1.50)
RAM_REQUIREMENT_RANGE = (0.50, 4.00)
BANDWIDTH_REQUIREMENT_RANGE = (0.01, 0.40)
TIME_IN_RESERVE_RANGE = (0.10, 1.00)
INTERACTION_GB_RANGE = (0.00005, 0.005)
FUNCTIONAL_UNITS = 25_000_000

# Controlled scenarios: fit nodes are service-specific; dirty nodes are feasible
# alternatives; broken nodes have no capacity. Fit CPU/RAM vectors are
# pairwise incomparable, preventing service co-location.
CONTROLLED_FIT_PROFILE = {
    "power_per_cpu": 0.003,
    "expected_lifetime": 4.0,
    "embodied_emissions_per_cpu": 62.5,
    "pue": 1.1,
    "carbon_intensity": 0.10,
}
CONTROLLED_DIRTY_PROFILE = {
    "power_per_cpu": 0.009,
    "expected_lifetime": 2.0,
    "embodied_emissions_per_cpu": 62.5,
    "pue": 1.6,
    "carbon_intensity": 0.90,
}
CONTROLLED_SHORT_LINK_KM = 1.0
CONTROLLED_LONG_LINK_KM = 1000.0
