# Experimental setup

## Objective

The experiment compares placement heuristics on synthetic microservice
applications and Cloud-Edge infrastructures. Each placement is evaluated using
component SCI and network SCI at a single static snapshot. Update policies and
runtime migrations are outside the current experiment.

## Applications

Each application is generated from one seed, one size, and one graph topology.
Independent deterministic random streams generate graph structure, interaction
traffic, and service requirements. For a fixed seed and size, changing topology
therefore does not also change service-resource requirements.

| Parameter | Values |
|---|---|
| Seeds | `151195`, `30997`, `50296`, `42`, `21297` |
| Services | 10, 20, 40 |
| Topologies | Erdős–Rényi, Barabási–Albert, Watts–Strogatz |
| Endpoints | 6 |
| Functional units | 25,000,000 per year |

Application graphs use the native NetworkX generators. Their parameters are
`p = 0.20` for Erdős–Rényi, `m = 2` for Barabási–Albert, and `k = 4`, with
rewiring probability `0.15`, for Watts–Strogatz. Disconnected components are
joined after generation so every generated application is connected.

Each service independently receives the following requirements:

| Requirement | Range | Unit |
|---|---:|---|
| CPU | 0.25–1.50 | vCPU |
| RAM | 0.50–4.00 | GB |
| Inbound bandwidth | 0.01–0.40 | Gbit/s |
| Outbound bandwidth | 0.01–0.40 | Gbit/s |
| Time in reserve | 0.10–1.00 | years |

Each application edge becomes an endpoint interaction. Its average traffic is
sampled uniformly between 0.00005 and 0.005 GB, corresponding to approximately
50 KB–5 MB. Edges are distributed over the six endpoints, whose invocation
probabilities are random and normalized to sum to one.

## Infrastructure graphs

Infrastructure sizes are 16, 32, 64, and 128 nodes. Three density levels are
available:

| Density | Target mean degree |
|---|---:|
| Sparse | 2 |
| Medium | 4 |
| Dense | 8 |

Density is translated into generator parameters as follows:

- Erdős–Rényi: `p = target mean degree / (nodes - 1)`;
- Barabási–Albert: `m` is approximately half the target mean degree;
- Internet AS: target edges are `nodes × target mean degree / 2`.

All infrastructure structures come from the native NetworkX
[`erdos_renyi_graph`](https://networkx.org/documentation/stable/reference/generated/networkx.generators.random_graphs.erdos_renyi_graph.html),
[`barabasi_albert_graph`](https://networkx.org/documentation/stable/reference/generated/networkx.generators.random_graphs.barabasi_albert_graph.html),
and
[`random_internet_as_graph`](https://networkx.org/documentation/stable/reference/generated/networkx.generators.internet_as_graphs.random_internet_as_graph.html)
generators. NetworkX also computes connected components and weighted shortest
paths. Disconnected Erdős–Rényi components are joined before assigning link
distances.

The Internet-AS generator runs successfully at the experiment sizes, although its
documented target range is 1,000–10,000 nodes. The generated graph is used as
the structural base; non-bridge edges are removed or missing edges are added to
reach the selected target density while preserving connectivity.

With `FIX_TOPOLOGY_DENSITY = True`, the default experiment uses three scenarios:

| Topology | Density |
|---|---|
| Erdős–Rényi | Dense |
| Barabási–Albert | Medium |
| Internet AS | Sparse |

Setting `FIX_TOPOLOGY_DENSITY = False` evaluates all nine topology-density
combinations while retaining the same density formulas.

Physical-link distances are sampled uniformly between 20 and 1,200 km. Routes
between every node pair use shortest-path distance over the generated physical
graph.

## Node profiles

Hardware composition is fixed for each infrastructure size and assignments are
shuffled using the experiment seed. This prevents hardware-composition changes
from confounding topology comparisons.

Independent random streams generate hardware assignment, graph structure, link
distances, and site properties. Node profiles, expected lifetime, PUE, and
carbon intensity therefore remain identical across topology scenarios with the
same seed and size.

| Profile | Share | vCPU | RAM (GB) | Bandwidth (Gbit/s) | kW per vCPU | Embodied (kgCO2eq) |
|---|---:|---:|---:|---:|---:|---:|
| Edge small | 30% | 2 | 4 | 1 | 0.003 | 100 |
| Edge medium | 30% | 4 | 8 | 2.5 | 0.004 | 160 |
| Edge large | 20% | 8 | 16 | 5 | 0.005 | 260 |
| Cloud medium | 15% | 16 | 32 | 10 | 0.007 | 420 |
| Cloud large | 5% | 32 | 64 | 25 | 0.009 | 600 |

Largest-remainder allocation gives these concrete compositions:

| Nodes | Edge small | Edge medium | Edge large | Cloud medium | Cloud large |
|---:|---:|---:|---:|---:|---:|
| 16 | 5 | 5 | 3 | 2 | 1 |
| 32 | 10 | 10 | 6 | 5 | 1 |
| 64 | 19 | 19 | 13 | 10 | 3 |
| 128 | 39 | 38 | 26 | 19 | 6 |

Expected lifetime remains uniformly distributed between 3 and 7 years. PUE is
sampled between 1.05 and 1.60, and site carbon intensity between 0.03 and 0.70
kgCO2eq/kWh. These are site properties and therefore remain independent of the
hardware profile. Storage is not represented by the current model.

## SCI calculation

Component operational energy is calculated as:

`PUE × runtime hours × power per vCPU × requested vCPU`.

Operational carbon multiplies this energy by the node carbon intensity.
Component embodied carbon allocates node manufacturing emissions according to
the service runtime fraction and its share of node CPU. Component SCI divides
the resulting endpoint-weighted carbon by 25,000,000 functional units.

For each inter-service interaction placed on different nodes, network carbon is:

`average GB × reference kgCO2eq/GB × route distance / 700 km`.

The reference profiles are:

| Profile | Operational kgCO2eq/GB | Embodied kgCO2eq/GB |
|---|---:|---:|
| RENATER Montpellier peak | 0.000793 | 0.000493 |
| RENATER Montpellier off-peak | 0.001400 | 0.000493 |

Network embodied emissions are disabled in the main grid. Enabling
`INCLUDE_NETWORK_EMBODIED` restores the reference embodied coefficient without
changing the model.

Each result contains `objective_sci`, `total_sci`, `component_sci`,
`component_operational_sci`, `component_embodied_sci`, `network_sci`,
`network_operational_sci`, and `network_embodied_sci`. `objective_sci` follows
the selected scope; `total_sci` always includes components and network. The
legacy `sci` column remains an alias of `objective_sci`.

## Placement heuristics

The grid evaluates twelve configurations:

- `capacityonly(k)` with `k` equal to 1, 100, and 1,000;
- `greenonly(k)` with `k` equal to 1, 100, and 1,000;
- `networkaware(alpha,beta,gamma)` with balanced, green-dominant,
  capacity-dominant, and centrality-dominant weights;
- `scigreedy`;
- `scilocalsearch`.

Network-aware weights are `(0.33, 0.33, 0.34)`, `(0.60, 0.20, 0.20)`,
`(0.20, 0.60, 0.20)`, and `(0.20, 0.20, 0.60)`. Every heuristic is evaluated
with `components_only` and `components_and_network` scopes.

## Grid size

The default fixed topology-density setup contains 25,920 trials:

`5 seeds × 3 application sizes × 3 application topologies × 4 infrastructure sizes × 3 infrastructure scenarios × 12 heuristics × 2 scopes × 2 route profiles`.

The full topology-density product contains 77,760 trials.

## Validation

Profile counts were checked for every infrastructure size. Network-aware
placements were tested over all application sizes, infrastructure sizes, and
three fixed infrastructure scenarios. All 36 combinations produced a valid
placement; easy cases used one node, while larger cases used multiple nodes and
exposed both component-dominated and network-dominated SCI. With the final
NetworkX generators, this validation used between one and nine nodes and
network SCI accounted for between 0% and 81.5% of total SCI. Here, nodes used
means the number of distinct infrastructure nodes containing at least one
service, not the number of nodes available. These measurements refer to the
balanced network-aware heuristic, seed 42, and the 36 combinations of
application size, infrastructure size, and fixed infrastructure scenario.

All twelve heuristic configurations were also executed successfully with 40
services and 128 nodes on the sparse Internet-AS scenario. In that local test,
most configurations completed within five seconds; `scilocalsearch` required
approximately 163 seconds. The full Ray Tune grid has not been executed.

## Outputs

Each Ray Tune trial stores generated `application.pl` and `infrastructure.pl`
files under its own `output/` directory. Trial dictionaries are merged by Ray
Tune and saved to:

`results/parquets/network-sci/raw-sci-aware.parquet`.

The result dictionary contains flat columns for every selected experimental
dimension and the fixed generator parameters needed to interpret it. Ray also
stores the original nested trial configuration in `params.json` and exposes it
through `config/...` columns in the merged DataFrame.

For direct filtering, parameterized heuristic names are also split into
`heuristic_name`, `top_k`, `green_weight`, `capacity_weight`, and
`centrality_weight`. The concrete number of nodes assigned to each hardware
profile is stored in separate `*_nodes` columns.

Generated-instance statistics are retained as columns as well: application
edge count, actual endpoint count, average interaction volume, expected traffic
per invocation, physical-link count, actual mean degree, and average and maximum
route distances. This distinguishes configured targets from values produced by
the random graph generators.
