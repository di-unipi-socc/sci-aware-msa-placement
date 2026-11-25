# Experimental setup

## Random instances

All experiments use random instances. The generator preserves the pre-existing
random setup, with no artificial node classes, service-slot limits, power
calibration or guaranteed placement. Node and route facts are shuffled using the
scenario seed. Applications use ER or BA graphs with 10, 20 or 40 services, or
Online Boutique's 10-service topology and endpoint probabilities. Synthetic
applications distribute their interactions over up to six endpoints.

| Application parameter | Range |
|---|---|
| CPU | 0.25–1.50 vCPU |
| RAM | 0.50–4 GB |
| Inbound/outbound bandwidth | 0.01–0.40 each |
| Time in reserve | 0.10–1.00 |
| Interaction volume | 0.00005–0.005 GB/invocation |
| Functional units | 25,000,000/year |

CPU and RAM are independently sampled; services can share nodes subject to
CPU, RAM and inbound/outbound bandwidth capacities. Endpoint probabilities
weight both component and network contributions. Component incidence counts
one occurrence per service per endpoint; network SCI counts every interaction.

| Node profile | Share | vCPU | RAM GB | Bandwidth | kW/vCPU | Embodied kgCO2eq |
|---|---:|---:|---:|---:|---:|---:|
| edge_small | 30% | 2 | 4 | 1 | 0.003 | 125 |
| edge_medium | 30% | 4 | 8 | 2.5 | 0.004 | 250 |
| edge_large | 20% | 8 | 16 | 5 | 0.005 | 500 |
| cloud_medium | 15% | 16 | 32 | 10 | 0.007 | 1000 |
| cloud_large | 5% | 32 | 64 | 25 | 0.009 | 2000 |

Node counts use largest-remainder allocation and shuffled profile assignments.
Lifetime is uniform over 2–4 years, PUE over 1.1–1.6 and CI over 0.03–0.9.
Physical links sample 5–1,000 km. Infrastructure sizes are 16, 32, 64, 128, 256
and 512 nodes; native NetworkX ER, BA and Internet-AS generators are used.
Fixed topology/density pairs are ER/dense, BA/medium and IAAG/sparse, targeting
mean degrees 8, 4 and 2. `FIX_TOPOLOGY_DENSITY = False` enables their Cartesian
product. Disconnected components are joined; all-pairs shortest-path distances
are written as end-to-end `route/4` facts. All app/infra-size combinations are
retained, including applications with more services than infrastructure nodes.

RENATER Montpellier peak/off-peak coefficients are respectively 0.000793 and
0.001400 kgCO2eq/GB, normalized to 700 km. Network embodied is disabled by
default; when enabled, its coefficient is 0.000493 kgCO2eq/GB. Component embodied
continues to be included, following the original Prolog formula.

## OR-Tools/SCIP optimum

`optimum` is a separate Python baseline, not a Prolog placement heuristic.
Binary x(service,node) variables enforce exactly one node per service; four
resource constraints per node enforce CPU/RAM/bandwidth capacities. Individually
ineligible assignments are omitted. Component costs match the Prolog formulas,
including time in reserve, per-endpoint incidence weights, embodied allocation
and functional-unit normalization. Structured inputs use the same numeric
precision as generated Prolog facts.

For the combined scope, each interacting service pair has a continuous unit
flow on the directed arcs of the generated physical graph. At node n,
outflow minus inflow equals x(source,n) minus x(target,n). Arc cost is expected
GB per invocation times the selected emissions reference times distance/700.
With integral endpoint assignments, the minimum flow cost is the shortest-path
cost, exactly the routing model used in Prolog, up to floating-point rounding.
Co-located endpoints need no flow. Link capacities are not added: the Prolog
model constrains node bandwidth, not physical-link aggregate traffic.
This formulation avoids service-pair × node-pair product variables.

`MILP_TIMEOUT_SECONDS = None` leaves SCIP without a time limit (default). A
positive value sets a solve limit in seconds. A timed-out incumbent is never
used as a certified optimum. Relative and absolute MIP gap limits are zero;
feasibility tolerance, objective scaling and thread count are in `config.py`.
An optimum is accepted only with solver status `OPTIMAL`; infeasibility and
other statuses remain explicit failed baseline rows. Optimality is certified
within the solver's numerical tolerances, not exact rational arithmetic.
Every returned placement is validated and its four SCI contributions are
recomputed by Prolog. MILP and Prolog objectives must agree within configured
tolerances or the trial fails validation. Large instances may remain running
or exhaust memory; there is no fallback to an unproven incumbent.

## Grid and reference matching

Five seeds, seven application configurations, six infrastructure sizes and
three fixed network scenarios produce 630 generated instances. With two route
profiles there are 1,260 case configurations. Each has 14 heuristic/scope trials
and two optimum trials (one per scope): **20,160 trials**, comprising 17,640
heuristic runs and 2,520 baseline runs. `capacityonly` and `greenonly` use
K=1/100/1000; `networkaware` uses four configured weight triples; SCI-greedy and
local search run under both scopes. Network-aware and top-k run once under the
combined scope. No exhaustive enumeration is part of the experimental grid.

A baseline is solved once per full case/scope, independently of heuristic
trials. The final Parquet joins successful certified baseline rows to matching
heuristic rows, including seed, app topology/size, infrastructure topology,
density/size, route profile/coefficient, network-embodied setting and scope.
No baseline is inferred from the best heuristic. In partial results, missing
or failed baseline references remain null. Gap/ratio are computed only for
available references. Negative gaps beyond numerical tolerance are rejected.
The two `optimal_components_*_sci` totals are separate scope-specific minima;
the selected optimal SCI breakdown and placement always match the row's scope.

## Outputs and execution

Run `uv sync`, start Ray and run `uv run experiments`. Restart a pre-existing
Ray cluster after updating the code. The new name `network-sci-milp-v1` keeps
Ray state separate from earlier runs. Resume settings remain configurable.
Generated Prolog inputs use trial-local temporary directories; debug inputs
remain under `DEBUG_DIR`.

Final output: `results/parquets/network-sci-milp-v1/raw-sci-aware.parquet`.
Rows retain all four measured SCI contributions, execution status, placement,
reference values and gaps. Optimum rows also retain solver version/status,
objective, bound, model/solve wall time, variable/constraint counts and search
nodes. Heuristic `time` is Prolog CPU time; optimum `time` is model construction
plus solver wall time. Do not interpret these clocks as identical measurements.
The notebook uses this new experiment name and compares `optimum` with heuristics.

OR-Tools MIP documentation: https://developers.google.com/optimization/mip/mip_example
