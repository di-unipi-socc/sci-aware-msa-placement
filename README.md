# SCI-aware Micro-service Application placement

SCI-aware MSA placement is an experimental framework for evaluating microservice
application placement strategies under [Software Carbon Intensity](https://sci.greensoftware.foundation)
 (SCI)-aware objectives.

The project adopts a declarative methodology based on SWI-Prolog to model
microservice applications, infrastructure resources, placement constraints, and
SCI-aware optimisation goals. Placement strategies are expressed as logical
predicates, making the decision process explicit, inspectable, and extensible.

## Repo structure

```text
.
├── data/
│   ├── applications/              # Prolog application examples
│   └── infrastructures/           # Prolog infrastructure examples
├── prolog/                        # Placement model, heuristics, and Prolog utilities
├── results/
│   ├── notebooks/                 # Result cleaning and plotting notebooks
│   └── parquets/                  # Raw experiment outputs
├── sci_aware_msa_placement/
│   ├── builder.py                 # Application and infrastructure generation
│   ├── config.py                  # Ray grid and generator parameters
│   ├── experiment.py              # Single experiment execution
│   ├── main.py                    # Ray Tune entrypoints
│   └── utils.py                   # Shared parsing and path helpers
└── README.md
```

## How to use
### Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/) for dependency management
- [SWI-Prolog](https://www.swi-prolog.org/) available on `PATH`

Install the Python dependencies:

```bash
uv venv # recommended to avoid conflicts with system packages
uv sync
```

### Run the Full Experiment

Start or connect to a Ray cluster, then run the main entrypoint:

```bash
uv run ray start --head --port 0
uv run experiments
```

Run the single configuration defined as `DEBUG_CONFIG` in `config.py` with:

```bash
uv run --active debug
```

Its generated inputs remain available in `debug-dir/`. Change `DEBUG_DIR` in
`sci_aware_msa_placement/config.py` to use another location.

Results are saved as:

```text
results/parquets/network-sci-controlled/raw-sci-aware.parquet
```

Each Ray Tune trial generates its Prolog inputs in a temporary directory and
deletes them after execution. Its result dictionary is collected with the
other trials in the final Parquet file. Debug inputs remain available in
`debug-dir/`.

The Ray Tune search space is defined in
`sci_aware_msa_placement/config.py` and covers:

- synthetic Erdős–Rényi and Barabási–Albert applications with 10, 20, and 40 services
- the 10-service Online Boutique topology with randomized requirements and traffic
- synthetic infrastructures with 16, 32, 64, 128, 256, and 512 nodes
- native NetworkX Erdős–Rényi, Barabási–Albert, and Internet AS graphs
- sparse, medium, and dense infrastructures with target mean degree 2, 4, and 8
- fixed topology-density scenarios by default: ER-dense, BA-medium, and AS-sparse
- component-only and component-plus-network SCI
- controlled known-optimum, top-k, network-aware, SCI-greedy, and SCI local-search placements
- multiple seeds, top-k values, and network-aware weights
- RENATER Montpellier peak and off-peak route profiles
- network embodied emissions fixed to zero
- controlled fit, dirty, and broken node profiles; infeasible app/infra-size pairs are excluded
- component and network operational and embodied SCI outputs

Each scenario has one fit node per service. CPU/RAM requirements prevent
co-location, fit nodes have lower component SCI, and routes between fit nodes
are shorter than routes involving dirty or broken nodes. The all-fit placement
therefore provides a known optimum for both scopes. Its SCI breakdown and
placement are included in every trial result; `exhaustive` is no longer run.

Set `FIX_TOPOLOGY_DENSITY = False` in `config.py` to evaluate all nine
topology-density combinations instead of the three fixed scenarios.

Existing Ray Tune state is restored by default. Unfinished trials resume and
errored trials restart according to the `RESUME_*` and
`RESTART_ERRORED_TRIALS` settings in `config.py`.

The new experiment uses the `network-sci-controlled` output name, so it does
not restore the previous `network-sci-exhaustive` Ray run.

### Analyse Results

The notebook in `results-network/` reads the compact Parquet schema and derives
aggregate SCI values from the four stored atomic SCI columns:

```text
results-network/analyse.ipynb
```

## Citation

The accompanying paper:

> [Jacopo Massa](https://pages.di.unipi.it/massa), [Stefano Forti](https://pages.di.unipi.it/forti), Sara Bruschi, [Jacopo Soldani](https://pages.di.unipi.it/soldani), [Antonio Brogi](https://pages.di.unipi.it/brogi)<br>
> **SCI-aware application placement in the cloud-edge continuum**, <br>	
> [12th European Conference on Service-Oriented and Cloud Computing](https://conf.researchr.org/home/esocc-2026), ESOCC 2026.

has been accepted for publication, other metadata will be added here once available.
