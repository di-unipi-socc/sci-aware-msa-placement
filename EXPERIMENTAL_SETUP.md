# Experimental setup

## Objective

Compare placement heuristics on synthetic microservice applications and
Cloud-Edge infrastructures at one static snapshot. `SCENARIO_MODE` selects
`random` (default) or `controlled`. Only controlled scenarios have a known
optimal placement. Random generation restores the parameters and sampling
from commit `747767d`, before controlled scenarios were introduced.

## Random scenarios

Service CPU (0.25–1.50 vCPU) and RAM (0.50–4 GB) requirements are sampled
independently. Nodes can host multiple services, subject to all resource limits.
Infrastructure profiles are assigned by largest-remainder allocation and shuffled:

| Profile | Share | vCPU | RAM GB | Bandwidth | kW/vCPU | Embodied kgCO2eq |
|---|---:|---:|---:|---:|---:|---:|
| edge_small | 30% | 2 | 4 | 1 | 0.003 | 125 |
| edge_medium | 30% | 4 | 8 | 2.5 | 0.004 | 250 |
| edge_large | 20% | 8 | 16 | 5 | 0.005 | 500 |
| cloud_medium | 15% | 16 | 32 | 10 | 0.007 | 1000 |
| cloud_large | 5% | 32 | 64 | 25 | 0.009 | 2000 |

Lifetime is uniform over 2–4 years, PUE over 1.1–1.6, carbon intensity over
0.03–0.9, and physical-link distances over 5–1,000 km. Node resources are
independent of application requirements. All app/infra-size pairs are included,
giving 630 scenarios and 14 heuristic/scope configurations: **17,640 trials**
with two route profiles. Neither `controlled` nor `exhaustive` runs in random
mode. Optimal-reference fields are null; all four measured SCI contributions
are retained. `scenario_mode` is stored in Ray configuration and the Parquet.

The random run is named `network-sci-random-v1`; changing the mode also changes
the default run name. Restart Ray after updating the code on a running cluster.

## Applications

The grid includes synthetic Erdős–Rényi and Barabási–Albert applications with
10, 20, or 40 services, plus Online Boutique's 10-service topology. Synthetic
applications use six endpoints; Online Boutique keeps its endpoint groups and
probabilities. Interaction volumes are sampled from 0.00005–0.005 GB, and
endpoint probabilities are normalized to one. Functional units remain
25,000,000 per year.

In controlled mode, service CPU requirements are sampled within 0.25–1.50 vCPU, sorted in
increasing order; RAM requirements are sampled within 0.50–4 GB, sorted in
decreasing order. This makes each service's CPU/RAM requirement vector
incomparable with every other service's vector. Bandwidth and time-in-reserve
remain independently sampled from their configured ranges. The incomparable
vectors prevent two services from sharing any generated node.

## Controlled infrastructure and known optimum

Each service has a dedicated **fit** node whose capacities equal that service's
requirements. Extra nodes are split between **dirty** alternatives, whose
capacities match selected service requirements, and **broken** nodes with zero
capacity. Each fit and dirty node samples its component parameters uniformly
from separate, non-overlapping ranges:

| Profile | kW/vCPU | Lifetime (years) | Embodied kgCO2eq/vCPU | PUE | Carbon intensity |
|---|---:|---:|---:|---:|---:|
| Fit | 0.0025–0.0045 | 4–6 | 50–62.5 | 1.05–1.25 | 0.03–0.20 |
| Dirty | 0.006–0.009 | 2–3 | 62.6–80 | 1.30–1.60 | 0.40–0.90 |

Broken nodes receive a shuffled, as-even-as-possible mix of fit-like and
dirty-like energy profiles while retaining zero capacity. The embodied ranges
bracket the cloud-large reference of 2,000 kgCO2eq over 32 vCPU. Even at the
range limits, fit nodes have lower operational factors (at most 0.001125 versus
at least 0.00312) and embodied factors per vCPU-year (at most 15.625 versus at
least 20.87). Thus every eligible fit placement remains better on component SCI.
All profile and link draws use deterministic random streams derived from the
scenario seed, so placements are compared on the same generated infrastructure.

The generated physical topology still follows the selected NetworkX graph and
density. Fit-fit links sample 1–5 km; links involving a dirty or broken node
sample 700–1,000 km. The lower bound for long links is raised when needed to
remain above the longest possible fit-chain route. This keeps every fit-to-fit
shortest route shorter than any route involving an alternative node.

The fit placement is optimal for both objectives: fit nodes have lower
component operational and embodied SCI than dirty nodes, and fit-to-fit routes
have lower network SCI than routes involving alternatives. Co-location cannot
lower network SCI because the CPU/RAM requirement vectors permit at most one
service per node. Broken nodes are ineligible. The generator records this fit
placement in Prolog, and each trial evaluates its component/network SCI using
the same SCI predicates used for heuristic placements.

The search space excludes infrastructure sizes smaller than the service count
plus two nodes, ensuring room for at least one dirty and one broken node. With
the current grid this leaves 540 application/infrastructure/seed scenarios.

## Infrastructure topologies

Infrastructure sizes are 16, 32, 64, 128, 256, and 512 nodes. Fixed
topology-density pairs are ER-dense, BA-medium, and Internet-AS-sparse. Set
`FIX_TOPOLOGY_DENSITY = False` to evaluate all nine combinations. NetworkX
generates each graph; disconnected components are joined before the controlled
link distances are assigned.

The route profiles use the RENATER Montpellier reference coefficients:

| Profile | Operational kgCO2eq/GB | Embodied kgCO2eq/GB |
|---|---:|---:|
| Peak | 0.000793 | 0.000493 |
| Off-peak | 0.001400 | 0.000493 |

Network embodied emissions are disabled by default. The configuration can
enable them without changing the generated topology.

## Placement heuristics and grid size

The controlled grid includes `controlled` as the known-optimum baseline, `capacityonly(k)`
and `greenonly(k)` for `k = 1, 100, 1000`, four `networkaware` weight settings,
`scigreedy`, and `scilocalsearch`. Scope is varied for `controlled`,
`scigreedy`, and `scilocalsearch`; other heuristics run once with
`components_and_network`.

There are 16 heuristic/scope configurations, two route profiles, and 540
scenarios: **17,280 trials**. The `exhaustive` heuristic is not in this grid.

## Results and debug

Every successful controlled experiment stores the heuristic's four SCI components,
the known-optimum SCI components, the optimal total for both scopes, and the known
placement. The `optimal_sci` column selects the reference matching that trial's
scope. Generated-instance statistics and execution status are also retained.
Ray configuration fields are flattened into the final Parquet for filtering.

The controlled grid writes to:

`results/parquets/network-sci-controlled-v1/raw-sci-aware.parquet`

The random grid writes to:

`results/parquets/network-sci-random-v1/raw-sci-aware.parquet`

Debug mode runs the single `DEBUG_CONFIG`; generated Prolog inputs remain in
`debug-dir/`.
