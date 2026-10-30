# Experimental setup

## Objective

Compare placement heuristics on synthetic microservice applications and
Cloud-Edge infrastructures at one static snapshot. Each generated scenario has
a known optimal placement, so heuristic SCI can be compared with a reference
without running exhaustive search.

## Applications

The grid includes synthetic Erdős–Rényi and Barabási–Albert applications with
10, 20, or 40 services, plus Online Boutique's 10-service topology. Synthetic
applications use six endpoints; Online Boutique keeps its endpoint groups and
probabilities. Interaction volumes are sampled from 0.00005–0.005 GB, and
endpoint probabilities are normalized to one. Functional units remain
25,000,000 per year.

Service CPU requirements are sampled within 0.25–1.50 vCPU, sorted in
increasing order; RAM requirements are sampled within 0.50–4 GB, sorted in
decreasing order. This makes each service's CPU/RAM requirement vector
incomparable with every other service's vector. Bandwidth and time-in-reserve
remain independently sampled from their configured ranges. The incomparable
vectors prevent two services from sharing any generated node.

## Controlled infrastructure and known optimum

Each service has a dedicated **fit** node whose capacities equal that service's
requirements. Extra nodes are split between **dirty** alternatives, whose
capacities match selected service requirements, and **broken** nodes with zero
capacity. Fit and dirty nodes use fixed component profiles:

| Profile | kW/vCPU | Lifetime (years) | Embodied kgCO2eq/vCPU | PUE | Carbon intensity |
|---|---:|---:|---:|---:|---:|
| Fit | 0.003 | 4 | 62.5 | 1.1 | 0.10 |
| Dirty | 0.009 | 2 | 62.5 | 1.6 | 0.90 |

The embodied value scales the existing cloud-large reference of 2,000 kgCO2eq
over 32 vCPU. Fit and dirty use the low/high ends of the configured power range;
their lifetimes, PUE, and carbon intensity keep both component SCI terms lower
on fit nodes.

The generated physical topology still follows the selected NetworkX graph and
density. Fit nodes are connected by short links of 1 km; all links involving a
dirty or broken node are 1,000 km. This makes every fit-to-fit shortest route
shorter than any route involving an alternative node.

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

The grid includes `controlled` as the known-optimum baseline, `capacityonly(k)`
and `greenonly(k)` for `k = 1, 100, 1000`, four `networkaware` weight settings,
`scigreedy`, and `scilocalsearch`. Scope is varied for `controlled`,
`scigreedy`, and `scilocalsearch`; other heuristics run once with
`components_and_network`.

There are 16 heuristic/scope configurations, two route profiles, and 540
scenarios: **17,280 trials**. The `exhaustive` heuristic is not in this grid.

## Results and debug

Every successful experiment stores the heuristic's four SCI components, the
known-optimum SCI components, the optimal total for both scopes, and the known
placement. The `optimal_sci` column selects the reference matching that trial's
scope. Generated-instance statistics and execution status are also retained.
Ray configuration fields are flattened into the final Parquet for filtering.

The full grid writes to:

`results/parquets/network-sci-controlled/raw-sci-aware.parquet`

Debug mode runs the single `DEBUG_CONFIG`; generated Prolog inputs remain in
`debug-dir/`.
