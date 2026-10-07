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
uv run --active sci-aware 
```

Run the single configuration defined as `DEBUG_CONFIG` in `config.py` with:

```bash
uv run --active debug
```

Results are saved as:

```text
results/parquets/network-sci/raw-sci-aware.parquet
```

The Ray Tune search space is defined in
`sci_aware_msa_placement/config.py` and covers:

- synthetic applications with 10, 20, and 40 services
- synthetic infrastructures with 16, 32, and 64 nodes
- Erdős–Rényi, Barabási–Albert, and Watts–Strogatz graphs
- component-only and component-plus-network SCI
- top-k, network-aware, SCI-greedy, and SCI local-search placements
- multiple seeds, top-k values, and network-aware weights
- RENATER Montpellier peak and off-peak route profiles
- zero or reference-value network embodied emissions

### Analyse Results

Use the notebooks in `results/notebooks/` to clean raw parquet outputs and
generate plots:

```text
results/notebooks/clean-raw.ipynb
results/notebooks/plot.ipynb
```

## Citation

The accompanying paper:

> [Jacopo Massa](https://pages.di.unipi.it/massa), [Stefano Forti](https://pages.di.unipi.it/forti), Sara Bruschi, [Jacopo Soldani](https://pages.di.unipi.it/soldani), [Antonio Brogi](https://pages.di.unipi.it/brogi)<br>
> **SCI-aware application placement in the cloud-edge continuum**, <br>	
> [12th European Conference on Service-Oriented and Cloud Computing](https://conf.researchr.org/home/esocc-2026), ESOCC 2026.

has been accepted for publication, other metadata will be added here once available.
