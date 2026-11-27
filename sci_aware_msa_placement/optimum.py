"""Exact placement MILP: binary assignments and continuous interaction flows."""

from collections import defaultdict
from math import ceil, isfinite
from time import perf_counter

from ortools.linear_solver import pywraplp

from sci_aware_msa_placement import config

SOLVER_COLUMNS = [
    "solver_status",
    "solver_version",
    "solver_objective_sci",
    "solver_bound_sci",
    "solver_model_seconds",
    "solver_solve_seconds",
    "solver_variables",
    "solver_constraints",
    "solver_nodes",
]


def component_costs(application, nodes):
    weights = dict.fromkeys(application["requirements"], 0.0)
    for probability, pairs, _ in application["endpoints"]:
        for service in {m for pair in pairs for m in pair}:
            weights[service] += probability
    costs = {}
    for service, requirements in application["requirements"].items():
        cpu = requirements[0]
        tir = application["service_times"][service]
        factor = weights[service] * tir / application["functional_units"]
        for node, data in nodes.items():
            if any(r > c for r, c in zip(requirements, data["resources"], strict=True)):
                continue
            operational = (
                factor
                * cpu
                * 365
                * 24
                * data["power_per_cpu"]
                * data["pue"]
                * data["carbon_intensity"]
            )
            embodied = (
                factor
                * data["embodied"]
                / data["lifetime"]
                * cpu
                / data["resources"][0]
            )
            costs[service, node] = operational + embodied
    return costs


def add_network_flows(solver, objective, assignments, application, network, parameters):
    traffic = defaultdict(float)
    for probability, pairs, volumes in application["endpoints"]:
        for (source, target), volume in zip(pairs, volumes, strict=True):
            if source != target:
                # Routes are symmetric and have no shared link-capacity constraints.
                pair = tuple(sorted((source, target)))
                traffic[pair] += probability * volume
    profile = parameters["route_profile"]
    intensity = profile["operational_per_gb"]
    if parameters["include_network_embodied"]:
        intensity += profile["embodied_per_gb"]
    if intensity == 0:
        return
    arcs = [
        (a, b, distance)
        for source, target, distance in network["links"]
        for a, b in [(source, target), (target, source)]
    ]
    for (source, target), volume in traffic.items():
        if volume == 0:
            continue
        balances = {
            node: solver.RowConstraint(0, 0, "") for node in network["nodes"]
        }
        for node, balance in balances.items():
            source_assignment = assignments.get((source, node))
            target_assignment = assignments.get((target, node))
            if source_assignment is not None:
                balance.SetCoefficient(source_assignment, -1)
            if target_assignment is not None:
                balance.SetCoefficient(target_assignment, 1)
        for index, (a, b, distance) in enumerate(arcs):
            flow = solver.NumVar(0, 1, f"f_{source}_{target}_{index}")
            balances[a].SetCoefficient(flow, 1)
            balances[b].SetCoefficient(flow, -1)
            objective.SetCoefficient(
                flow, config.MILP_OBJECTIVE_SCALE * volume * intensity * distance / 700
            )


def create_solver():
    solver = pywraplp.Solver.CreateSolver(config.MILP_SOLVER)
    if solver is None:
        raise RuntimeError(f"OR-Tools solver {config.MILP_SOLVER} is unavailable")
    if not solver.SetNumThreads(config.MILP_THREADS):
        raise RuntimeError("Unable to configure MILP solver threads")
    if not solver.SetSolverSpecificParametersAsString(config.MILP_SCIP_PARAMETERS):
        raise RuntimeError("Invalid SCIP configuration")
    if config.MILP_TIMEOUT_SECONDS is not None:
        if not isfinite(config.MILP_TIMEOUT_SECONDS) or config.MILP_TIMEOUT_SECONDS <= 0:
            raise ValueError("MILP_TIMEOUT_SECONDS must be None or a positive finite number")
        solver.SetTimeLimit(max(1, ceil(config.MILP_TIMEOUT_SECONDS * 1000)))
    return solver


def solve_optimum(application, network, parameters):
    started = perf_counter()
    solver = create_solver()
    costs = component_costs(application, network["nodes"])
    assignments = {key: solver.BoolVar(f"x_{key[0]}_{key[1]}") for key in costs}
    by_service, by_node = defaultdict(list), defaultdict(list)
    for (service, node), variable in assignments.items():
        by_service[service].append(variable)
        by_node[node].append((application["requirements"][service], variable))
    for service in application["requirements"]:
        constraint = solver.RowConstraint(1, 1, "")
        for variable in by_service[service]:
            constraint.SetCoefficient(variable, 1)
    for node, data in network["nodes"].items():
        candidates = by_node[node]
        for resource, capacity in enumerate(data["resources"]):
            constraint = solver.RowConstraint(-solver.infinity(), capacity, "")
            for requirements, variable in candidates:
                constraint.SetCoefficient(variable, requirements[resource])
    objective = solver.Objective()
    for key, variable in assignments.items():
        objective.SetCoefficient(variable, costs[key] * config.MILP_OBJECTIVE_SCALE)
    if parameters["scope"] == "components_and_network":
        add_network_flows(
            solver, objective, assignments, application, network, parameters
        )
    elif parameters["scope"] != "components_only":
        raise ValueError(f"Unknown scope: {parameters['scope']}")
    objective.SetMinimization()
    built = perf_counter()
    status = solver.Solve()
    finished = perf_counter()
    status_names = {
        solver.OPTIMAL: "optimal",
        solver.FEASIBLE: "feasible",
        solver.INFEASIBLE: "infeasible",
        solver.UNBOUNDED: "unbounded",
        solver.ABNORMAL: "abnormal",
        solver.NOT_SOLVED: "not_solved",
    }
    statistics = {
        "solver_status": status_names.get(status, f"status_{status}"),
        "solver_version": solver.SolverVersion(),
        "solver_objective_sci": None,
        "solver_bound_sci": None,
        "solver_model_seconds": built - started,
        "solver_solve_seconds": finished - built,
        "solver_variables": solver.NumVariables(),
        "solver_constraints": solver.NumConstraints(),
        "solver_nodes": solver.nodes(),
    }
    placement = None
    if status == solver.OPTIMAL:
        statistics["solver_objective_sci"] = (
            objective.Value() / config.MILP_OBJECTIVE_SCALE
        )
        statistics["solver_bound_sci"] = (
            objective.BestBound() / config.MILP_OBJECTIVE_SCALE
        )
        placement = [
            (service, node)
            for (service, node), var in assignments.items()
            if round(var.solution_value()) == 1
        ]
    return placement, statistics
