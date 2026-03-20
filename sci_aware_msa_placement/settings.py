from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
PROLOG_DIR = PROJECT_ROOT / "prolog"
RESULTS_DIR = PROJECT_ROOT / "results"
PARQUETS_DIR = RESULTS_DIR / "parquets"
APP_DIR = DATA_DIR / "applications"
INFRA_DIR = DATA_DIR / "infrastructures"

CSV_DIR = OUTPUT_DIR / "csv"
PLOTS_DIR = OUTPUT_DIR / "plots"

PL_SUFFIX = ".pl"
ENCODING = "utf-8"
EXPERIMENT_NAME = "sci-aware-4"

MAIN_PL = PROLOG_DIR / f"main{PL_SUFFIX}"

MODE_FILE_PREFIX = {
    "random": "rnd",
    "curated": "crtd",
}

PROLOG = {
    "application_query": "application(A, MS, EPs).",
    "microservice_query": "microservice({name}, rr(CPU, RAM, BWIN, BWOUT), TiR).",
    "count_microservices_query": "findall(M, microservice(_,_,_), L), length(L, N).",
    "timed_placement_query": "timedPlacement({mode}, App, P, SCI, N, Time).",
    "timed_placement_base_query": "timedPlacement(tempBase, App, {placement}, SCI, N, Time).",
    "carbon_intensity_fact": "carbon_intensity('{name}', {ci}).\n",
}

RESULT_KEYS = {
    "application": "application",
    "size": "size",
    "mode": "mode",
    "heuristic": "heuristic",
    "seed": "seed",
    "infrastructure_path": "infrastructure_path",
    "time": "time",
    "sci": "sci",
    "nodes_used": "nodes_used",
    "placement": "placement",
    "success": "success",
    "timeout": "timeout",
    "error": "error",
}

OPTIMAL_KEYS = {
    "microservice": "ms",
    "node": "node",
}

PLACEMENT_ARITY = 2
CURATED_EXTRA_NODE_PAIR_SIZE = 2

TIMEOUT = 900
