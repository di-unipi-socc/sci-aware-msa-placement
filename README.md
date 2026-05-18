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
│   └── applications/              # Prolog microservice application inputs
├── prolog/                        # Placement model and Prolog utilities
├── results/
│   ├── notebooks/                 # Result cleaning and plotting notebooks
│   └── parquets/                  # Raw experiment outputs
├── sci_aware_msa_placement/
│   ├── builder.py                 # Infrastructure instance generation
│   ├── experiment.py              # Single experiment execution
│   ├── main.py                    # Ray Tune entrypoints
│   ├── models.py                  # Domain models and experiment enums
│   ├── search_space.py            # Applications, seeds, sizes, and heuristics
│   ├── settings.py                # Project paths and Prolog query templates
│   └── utils.py                   # Shared parsing and path helpers
└── README.md
```

## How to use
### Requirements

- Python 3.11 or newer
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

The script asks for an experiment name. If left blank, it uses `sci-aware`.
Results are saved as:

```text
results/parquets/<experiment-name>/raw-sci-aware.parquet
```

The default search space is defined in
`sci_aware_msa_placement/search_space.py` and covers:

- applications: `demo`, `online-boutique`
- environment modes: random and curated
- infrastructure sizes from `2^5` to `2^20`
- exhaustive, baseline, and heuristic placement modes where applicable
- multiple random seeds

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
