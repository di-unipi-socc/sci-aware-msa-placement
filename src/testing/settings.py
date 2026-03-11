from pathlib import Path

# Settings for directory paths


def full_app_file(name: str) -> Path:
    """Returns the path to the full application file for a given application name."""
    return APP_DIR / name / "applicationFULLms.pl"


ROOT_DIR = Path(__file__).parent.parent.parent
RESOURCES_DIR = ROOT_DIR / "resources"
SRC_DIR = ROOT_DIR / "src"
PROLOG_DIR = SRC_DIR / "prolog"
MAIN_PL = PROLOG_DIR / "main.pl"

APP_DIR = RESOURCES_DIR / "applications"

INFRA_DIR = RESOURCES_DIR / "infrastructures"
INFRA_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_DIR = ROOT_DIR / "output"
CSV_DIR = OUTPUT_DIR / "csv"
CSV_DIR.mkdir(parents=True, exist_ok=True)

NUMBER_OF_RUNS = 5
TIMEOUT = 900  # 15 minutes
SIZES = [2**i for i in range(4, 21)]
SEEDS = [
    123457,
    654323,
    987652,
    567895,
    698081,
    123456,
    654321,
    987654,
    567890,
    698087,
]
