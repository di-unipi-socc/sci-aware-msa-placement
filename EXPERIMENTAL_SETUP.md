# Experimental setup

## Objective

Compare placement heuristics on synthetic microservice applications and
Cloud-Edge infrastructures at one static snapshot. `SCENARIO_MODE` selects
`random` or `controlled` (default). Only controlled scenarios have a known
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

The random run is named `network-sci-random-v2`; changing the mode also changes
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
vectors prevent a service from using another service's fit node. Dirty nodes
can host multiple services subject to their resource and service-count limits.

## Controlled infrastructure and known optimum

Each service has a dedicated **fit** node with capacities equal to its requirements.
Extra nodes are split approximately equally between dirty and broken nodes.
Within each class, half are near and half far (rounded for odd counts).
Broken nodes all use the green profile and have exactly one of CPU, RAM,
inbound or outbound bandwidth zero; their other resources remain positive.
Dirty capacities are the sum of the requirements of a randomly selected group
of two or three services. `nodeServiceLimit/2` also enforces a maximum of two
or three assigned services, independently of their individual sizes.

| Class | Power kW/vCPU | PUE | CI kgCO2eq/kWh | Location |
|---|---:|---:|---:|---|
| Fit | 0.0025–0.0045 | 1.05–1.25 | 0.03–0.20 | Near |
| Broken | 0.0025–0.0045 | 1.05–1.25 | 0.03–0.20 | Half near, half far |
| Dirty near | Calibrated Pmin–1.2 Pmin | 1.30–1.60 | 0.40–0.90 | Near |
| Dirty far | Calibrated Pmin–1.2 Pmin | 1.30–1.60 | 0.40–0.90 | Far |

Near-to-near physical links sample 1–5 km. Any link incident to a far node
samples 700–1,000 km, preventing a far node from acquiring a short bypass.
A fit chain and one short attachment per extra near node ensure connectivity
of the near subgraph. NetworkX still supplies the underlying topology.

Dirty power is deliberately artificial: compute the fit placement's network
SCI using the largest reference intensity among the configured route profiles.
For each service, compute its fit component SCI and the coefficient multiplying
`power × PUE × CI` in the actual component SCI formula. Choose a common factor
so a dirty placement's operational SCI alone exceeds 1.1 times the sum of that
service's fit component SCI and the entire fit network SCI. All dirty nodes use the same brown profile, regardless of location. Divide
this factor by the dirty profile's minimum PUE and CI to get Pmin (at least
0.006 kW/vCPU); sample power over Pmin–1.2 Pmin.

Every eligible move to a dirty node then costs more than even eliminating the
entire network contribution. Fit nodes only accept their dedicated service and
broken nodes are ineligible, so all-fit remains a global optimum for both scopes.
This certificate uses no placement enumeration. It includes the component
embodied term still present in Prolog; network embodied remains disabled by
default. Power calibration is shared across peak/off-peak profiles to keep
node attributes identical when comparing those profiles.

All generated `node/6` and `route/4` fact lists are shuffled in Python with
`rnd = random.Random(seed)` and `rnd.shuffle`, preserving predicate grouping.
Controlled node identifiers are also assigned through a seeded shuffle.
Inputs remain reproducible across heuristics and scopes.

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

`results/parquets/network-sci-controlled-v2/raw-sci-aware.parquet`

The random grid writes to:

`results/parquets/network-sci-random-v2/raw-sci-aware.parquet`

Debug mode runs the single `DEBUG_CONFIG`; generated Prolog inputs remain in
`debug-dir/`.
