import random
import re
from functools import cache
from pathlib import Path

import networkx as nx

from sci_aware_msa_placement import config


def build_application(parameters: dict, output_dir: Path) -> tuple[Path, str, dict]:
    seed = parameters["seed"]
    graph_rng = random.Random(seed)
    traffic_rng = random.Random(seed + 1_000_000)
    requirements_rng = random.Random(seed + 2_000_000)
    scenario = parameters["application"]
    size = scenario["size"]
    topology = scenario["topology"]
    if topology == "online_boutique":
        application = "onlineBoutique"
        services, endpoints, interaction_pairs, probabilities = (
            _online_boutique_topology()
        )
    else:
        application = f"synthetic_{topology}_{size}_{parameters['seed']}"
        services = [f"service_{index}" for index in range(size)]
        graph = _build_graph(size, topology, graph_rng)
        edges = list(graph.edges)
        traffic_rng.shuffle(edges)
        endpoint_count = min(config.ENDPOINT_COUNT, len(edges))
        endpoints = [f"endpoint_{index}" for index in range(endpoint_count)]
        interaction_pairs = [[] for _ in endpoints]
        for index, (source, target) in enumerate(edges):
            interaction_pairs[index % endpoint_count].append(
                (services[source], services[target])
            )
        weights = [traffic_rng.random() for _ in endpoints]
        total_weight = sum(weights)
        probabilities = [weight / total_weight for weight in weights]

    interactions = []
    interaction_volumes = []
    for pairs in interaction_pairs:
        endpoint_interactions = []
        endpoint_volumes = []
        for source, target in pairs:
            avg_gb = traffic_rng.uniform(*config.INTERACTION_GB_RANGE)
            endpoint_interactions.append(f"({source},{target},{_number(avg_gb)})")
            endpoint_volumes.append(avg_gb)
        interactions.append(endpoint_interactions)
        interaction_volumes.append(endpoint_volumes)

    lines = [
        f"application({application},[{','.join(services)}],[{','.join(endpoints)}]).",
        "",
    ]
    service_requirements, service_times, service_lines = _application_requirements(
        parameters, services, requirements_rng
    )
    lines.extend(service_lines)

    endpoint_lines = []
    probability_lines = []
    for endpoint, pairs, probability in zip(
        endpoints, interactions, probabilities, strict=True
    ):
        endpoint_lines.append(f"endpoint({endpoint},[{','.join(pairs)}]).")
        probability_lines.append(f"probability({endpoint},{_number(probability)}).")

    lines.extend(
        [
            "",
            *endpoint_lines,
            "",
            *probability_lines,
            "",
            f"functionalUnits({application},{config.FUNCTIONAL_UNITS}).",
        ]
    )
    path = output_dir / "application.pl"
    path.write_text("\n".join(lines) + "\n", encoding=config.ENCODING)
    all_volumes = [volume for volumes in interaction_volumes for volume in volumes]
    metadata = {
        "_service_requirements": service_requirements,
        "_application_data": {
            "service_times": service_times,
            "endpoints": list(
                zip(probabilities, interaction_pairs, interaction_volumes, strict=True)
            ),
        },
        "application_edges": sum(len(pairs) for pairs in interaction_pairs),
        "actual_endpoint_count": len(endpoints),
        "average_interaction_gb": sum(all_volumes) / len(all_volumes),
        "expected_traffic_gb_per_invocation": sum(
            probability * sum(volumes)
            for probability, volumes in zip(
                probabilities, interaction_volumes, strict=True
            )
        ),
    }
    return path, application, metadata


def _application_requirements(parameters, services, requirements_rng):
    lines = []
    mode = parameters.get("scenario_mode", config.SCENARIO_MODE)
    if mode == "controlled":
        cpu_requirements, ram_requirements = _incomparable_requirements(
            requirements_rng, len(services)
        )
    service_requirements = {}
    service_times = {}
    for index, service in enumerate(services):
        if mode == "controlled":
            cpu, ram = cpu_requirements[index], ram_requirements[index]
        else:
            cpu = requirements_rng.uniform(*config.CPU_REQUIREMENT_RANGE)
            ram = requirements_rng.uniform(*config.RAM_REQUIREMENT_RANGE)
        bandwidth_in = requirements_rng.uniform(*config.BANDWIDTH_REQUIREMENT_RANGE)
        bandwidth_out = requirements_rng.uniform(*config.BANDWIDTH_REQUIREMENT_RANGE)
        time_in_reserve = requirements_rng.uniform(*config.TIME_IN_RESERVE_RANGE)
        service_times[service] = time_in_reserve
        service_requirements[service] = (
            cpu,
            ram,
            bandwidth_in,
            bandwidth_out,
        )
        lines.append(
            f"microservice({service},rr({_number(cpu)},{_number(ram)},"
            f"{_number(bandwidth_in)},{_number(bandwidth_out)}),"
            f"{_number(time_in_reserve)})."
        )

    return service_requirements, service_times, lines


@cache
def _online_boutique_topology() -> tuple[
    list[str], list[str], list[list[tuple[str, str]]], list[float]
]:
    source = config.ONLINE_BOUTIQUE_PATH.read_text(encoding=config.ENCODING)
    source = re.sub(r"%.*", "", source)
    application = re.search(
        r"application\(onlineBoutique,\s*\[(.*?)\],\s*\[(.*?)\]\)\.",
        source,
        re.DOTALL,
    )
    services = _atoms(application.group(1))
    endpoints = _atoms(application.group(2))
    endpoint_bodies = dict(
        re.findall(r"endpoint\((\w+),\s*\[(.*?)\]\)\.", source, re.DOTALL)
    )
    interactions = [
        [
            (source_service, target_service)
            for source_service, target_service in re.findall(
                r"\(\s*(\w+)\s*,\s*(\w+)\s*,\s*[^)]+\)",
                endpoint_bodies[endpoint],
            )
        ]
        for endpoint in endpoints
    ]
    probability_by_endpoint = {
        endpoint: float(probability)
        for endpoint, probability in re.findall(
            r"probability\((\w+),\s*([0-9.]+)\)\.", source
        )
    }
    probabilities = [probability_by_endpoint[endpoint] for endpoint in endpoints]
    return services, endpoints, interactions, probabilities


def _atoms(raw_atoms: str) -> list[str]:
    return [atom.strip() for atom in raw_atoms.split(",")]


def _incomparable_requirements(
    rng: random.Random, count: int
) -> tuple[list[float], list[float]]:
    cpu_samples = set()
    ram_samples = set()
    while len(cpu_samples) < count:
        cpu_samples.add(rng.uniform(*config.CPU_REQUIREMENT_RANGE))
    while len(ram_samples) < count:
        ram_samples.add(rng.uniform(*config.RAM_REQUIREMENT_RANGE))
    return sorted(cpu_samples), sorted(ram_samples, reverse=True)


def build_network(
    parameters: dict,
    output_dir: Path,
    application: str,
    service_requirements: dict[str, tuple[float, float, float, float]],
    application_data: dict | None = None,
) -> tuple[Path, dict]:
    mode = parameters.get("scenario_mode", config.SCENARIO_MODE)
    if mode == "random":
        return _build_random_network(parameters, output_dir)
    if mode == "controlled":
        return _build_controlled_network(
            parameters, output_dir, application, service_requirements, application_data
        )
    raise ValueError(f"Unknown scenario mode: {mode}")


def _build_random_network(parameters: dict, output_dir: Path) -> tuple[Path, dict]:
    seed = parameters["seed"]
    profile_rng = random.Random(seed + 3_000_000)
    graph_rng = random.Random(seed + 4_000_000)
    distance_rng = random.Random(seed + 5_000_000)
    site_rng = random.Random(seed + 6_000_000)
    size = parameters["infrastructure_size"]
    graph = parameters["infrastructure_graph"]
    topology = graph["topology"]
    average_degree = config.AVERAGE_DEGREE_BY_DENSITY[graph["density"]]
    route_profile = parameters["route_profile"]
    embodied_per_gb = (
        route_profile["embodied_per_gb"]
        if parameters["include_network_embodied"]
        else 0.0
    )
    nodes = [f"node_{index}" for index in range(size)]
    profiles = _node_profiles(size, profile_rng)
    network = _build_graph(size, topology, graph_rng, average_degree)
    for source, target in network.edges:
        network[source][target]["distance"] = distance_rng.uniform(
            *config.LINK_DISTANCE_KM_RANGE
        )

    node_lines = []
    carbon_intensity_lines = []
    for node, node_profile in zip(nodes, profiles, strict=True):
        cpu = node_profile["cpu"]
        ram = node_profile["ram"]
        bandwidth_in = node_profile["bandwidth"]
        bandwidth_out = node_profile["bandwidth"]
        power = node_profile["power_per_cpu"]
        lifetime = site_rng.uniform(*config.EXPECTED_LIFETIME_RANGE)
        embodied = node_profile["embodied_emissions"]
        pue = site_rng.uniform(*config.PUE_RANGE)
        carbon_intensity = site_rng.uniform(*config.CARBON_INTENSITY_RANGE)
        node_lines.append(
            f"node({node},tor({cpu},{_number(ram)},{_number(bandwidth_in)},"
            f"{_number(bandwidth_out)}),{_number(power)},{_number(lifetime)},"
            f"{_number(embodied)},{_number(pue)})."
        )
        carbon_intensity_lines.append(
            f"carbon_intensity({node},{_number(carbon_intensity)})."
        )

    lines = [
        *node_lines,
        "",
        *carbon_intensity_lines,
    ]
    lines.extend(
        [
            "",
            f"routeProfile({route_profile['name']},"
            f"{route_profile['operational_per_gb']},"
            f"{embodied_per_gb}).",
            "",
        ]
    )
    distances = dict(nx.all_pairs_dijkstra_path_length(network, weight="distance"))
    for source in range(size):
        for target in range(size):
            if source != target:
                lines.append(
                    f"route({nodes[source]},{nodes[target]},"
                    f"{_number(distances[source][target])},"
                    f"{route_profile['name']})."
                )

    path = output_dir / "infrastructure.pl"
    _shuffle_infrastructure_facts(lines, seed)
    path.write_text("\n".join(lines) + "\n", encoding=config.ENCODING)
    route_distances = [
        distances[source][target]
        for source in range(size)
        for target in range(source + 1, size)
    ]
    metadata = {
        "physical_links": network.number_of_edges(),
        "actual_mean_degree": 2 * network.number_of_edges() / size,
        "average_physical_link_distance_km": (
            sum(attributes["distance"] for _, _, attributes in network.edges(data=True))
            / network.number_of_edges()
        ),
        "average_route_distance_km": sum(route_distances) / len(route_distances),
        "maximum_route_distance_km": max(route_distances),
    }
    return path, metadata


def _node_profiles(size: int, rng: random.Random) -> list[dict]:
    profiles = config.NODE_RESOURCE_PROFILES
    counts = node_profile_counts(size)
    assignments = [
        profile for profile in profiles for _ in range(counts[profile["name"]])
    ]
    rng.shuffle(assignments)
    return assignments


def node_profile_counts(size: int) -> dict[str, int]:
    profiles = config.NODE_RESOURCE_PROFILES
    weighted_counts = [size * profile["percentage"] for profile in profiles]
    counts = [count // 100 for count in weighted_counts]
    remaining = size - sum(counts)
    remainders = sorted(
        range(len(profiles)),
        key=lambda index: weighted_counts[index] % 100,
        reverse=True,
    )
    for index in remainders[:remaining]:
        counts[index] += 1
    return {
        profile["name"]: count for profile, count in zip(profiles, counts, strict=True)
    }


def _build_controlled_network(
    parameters: dict,
    output_dir: Path,
    application: str,
    service_requirements: dict[str, tuple[float, float, float, float]],
    application_data: dict,
) -> tuple[Path, dict]:
    seed = parameters["seed"]
    rnd = random.Random(seed)
    graph_rng = random.Random(seed + 4_000_000)
    profile_rng = random.Random(seed + 5_000_000)
    link_rng = random.Random(seed + 6_000_000)
    services = list(service_requirements)
    fit_count = len(services)
    size = parameters["infrastructure_size"]
    if size < fit_count + 2:
        raise ValueError("Controlled infrastructure needs fit, dirty, and broken nodes")
    if application_data is None:
        raise ValueError("Controlled power calibration requires application data")
    nodes = [f"node_{index}" for index in range(size)]
    rnd.shuffle(nodes)
    records = _controlled_nodes(nodes, services, service_requirements, rnd, profile_rng)
    graph = parameters["infrastructure_graph"]
    network = _build_graph(
        size,
        graph["topology"],
        graph_rng,
        config.AVERAGE_DEGREE_BY_DENSITY[graph["density"]],
    )
    network.add_edges_from((i, i + 1) for i in range(fit_count - 1))
    for i in range(fit_count, size):
        if records[i]["role"].endswith("near"):
            network.add_edge(i, link_rng.randrange(fit_count))
    for source, target in network.edges:
        far = records[source]["role"].endswith("far") or records[target][
            "role"
        ].endswith("far")
        bounds = (
            config.CONTROLLED_LONG_LINK_KM_RANGE
            if far
            else config.CONTROLLED_SHORT_LINK_KM_RANGE
        )
        network[source][target]["distance"] = link_rng.uniform(*bounds)
    distances = dict(nx.all_pairs_dijkstra_path_length(network, weight="distance"))
    required_factor = _controlled_operational_factor(
        service_requirements,
        application_data,
        records[:fit_count],
        distances,
        parameters,
    )
    for record in records[fit_count:]:
        if record["role"].startswith("dirty"):
            ci_min = config.CONTROLLED_DIRTY_PROFILE["carbon_intensity"][0]
            minimum_power = max(
                config.CONTROLLED_DIRTY_PROFILE["power_per_cpu"][0],
                required_factor / (ci_min * config.CONTROLLED_DIRTY_PROFILE["pue"][0]),
            )
            record["profile"]["power_per_cpu"] = profile_rng.uniform(
                minimum_power, minimum_power * config.CONTROLLED_POWER_RANGE_FACTOR
            )
    fit_facts = [
        f"fitNode({application},{m},{nodes[i]})." for i, m in enumerate(services)
    ]
    node_lines, carbon_lines, limit_lines = [], [], []
    for record in records:
        node, resources, profile = (
            record["node"],
            record["resources"],
            record["profile"],
        )
        hardware = ",".join(_number(v) for v in resources)
        embodied = profile["embodied_emissions_per_cpu"] * resources[0]
        node_lines.append(
            f"node({node},tor({hardware}),{_number(profile['power_per_cpu'])},"
            f"{_number(profile['expected_lifetime'])},{_number(embodied)},"
            f"{_number(profile['pue'])})."
        )
        carbon_lines.append(
            f"carbon_intensity({node},{_number(profile['carbon_intensity'])})."
        )
        limit_lines.append(f"nodeServiceLimit({node},{record['limit']}).")
    route_profile = parameters["route_profile"]
    embodied_per_gb = (
        route_profile["embodied_per_gb"]
        if parameters["include_network_embodied"]
        else 0.0
    )
    route_lines = [
        f"route({nodes[a]},{nodes[b]},{_number(distances[a][b])},{route_profile['name']})."
        for a in range(size)
        for b in range(size)
        if a != b
    ]
    lines = [
        *node_lines,
        "",
        *carbon_lines,
        "",
        *limit_lines,
        "",
        *fit_facts,
        "",
        f"routeProfile({route_profile['name']},{route_profile['operational_per_gb']},{embodied_per_gb}).",
        "",
        *route_lines,
    ]
    path = output_dir / "infrastructure.pl"
    _shuffle_infrastructure_facts(lines, seed)
    path.write_text("\n".join(lines) + "\n", encoding=config.ENCODING)
    route_distances = [distances[a][b] for a in range(size) for b in range(a + 1, size)]
    return path, {
        "physical_links": network.number_of_edges(),
        "actual_mean_degree": 2 * network.number_of_edges() / size,
        "average_physical_link_distance_km": sum(
            a["distance"] for _, _, a in network.edges(data=True)
        )
        / network.number_of_edges(),
        "average_route_distance_km": sum(route_distances) / len(route_distances),
        "maximum_route_distance_km": max(route_distances),
    }


def _controlled_nodes(nodes, services, service_requirements, rnd, profile_rng):
    size, fit_count = len(nodes), len(services)
    extra = size - fit_count
    dirty_count = (extra + 1) // 2
    broken_count = extra - dirty_count
    roles = (
        ["dirty_near"] * ((dirty_count + 1) // 2)
        + ["dirty_far"] * (dirty_count // 2)
        + ["broken_near"] * ((broken_count + 1) // 2)
        + ["broken_far"] * (broken_count // 2)
    )
    rnd.shuffle(roles)
    records = []
    for index, node in enumerate(nodes):
        role = "fit" if index < fit_count else roles[index - fit_count]
        if role == "fit":
            resources = service_requirements[services[index]]
            limit = 1
        else:
            limit = profile_rng.choice(config.CONTROLLED_DIRTY_SERVICE_LIMITS)
            group = profile_rng.sample(services, min(limit, fit_count))
            resources = tuple(
                sum(service_requirements[m][j] for m in group) for j in range(4)
            )
            if role.startswith("broken"):
                resources = list(resources)
                resources[profile_rng.randrange(4)] = 0
                resources = tuple(resources)
        ranges = (
            config.CONTROLLED_DIRTY_PROFILE
            if role.startswith("dirty")
            else config.CONTROLLED_FIT_PROFILE
        )
        profile = {key: profile_rng.uniform(*bounds) for key, bounds in ranges.items()}
        records.append(
            {
                "node": node,
                "role": role,
                "resources": resources,
                "profile": profile,
                "limit": limit,
            }
        )
    return records


def _controlled_operational_factor(
    requirements, application_data, fits, distances, parameters
):
    services = list(requirements)
    service_index = {m: i for i, m in enumerate(services)}
    weights = dict.fromkeys(services, 0.0)
    network_sci = 0.0
    profiles = [*config.ROUTE_PROFILES, parameters["route_profile"]]
    reference = max(
        profile["operational_per_gb"]
        + (profile["embodied_per_gb"] if parameters["include_network_embodied"] else 0)
        for profile in profiles
    )
    for probability, pairs, volumes in application_data["endpoints"]:
        for m in {m for pair in pairs for m in pair}:
            weights[m] += probability
        for (a, b), volume in zip(pairs, volumes, strict=True):
            network_sci += (
                probability
                * volume
                * reference
                * distances[service_index[a]][service_index[b]]
                / 700
            )
    factors = []
    for m, record in zip(services, fits, strict=True):
        weight = weights[m]
        if weight == 0:
            continue
        profile = record["profile"]
        cpu = requirements[m][0]
        tir = application_data["service_times"][m]
        coefficient = weight * cpu * tir * 365 * 24 / config.FUNCTIONAL_UNITS
        fit_sci = (
            coefficient
            * profile["power_per_cpu"]
            * profile["pue"]
            * profile["carbon_intensity"]
        )
        fit_sci += (
            weight
            * profile["embodied_emissions_per_cpu"]
            * cpu
            * tir
            / profile["expected_lifetime"]
            / config.FUNCTIONAL_UNITS
        )
        factors.append(
            config.CONTROLLED_NETWORK_MARGIN * (fit_sci + network_sci) / coefficient
        )
    return max(factors, default=0.0)


def _shuffle_infrastructure_facts(lines: list[str], seed: int) -> None:
    rnd = random.Random(seed)
    for prefix in ("node(", "route("):
        indices = [i for i, line in enumerate(lines) if line.startswith(prefix)]
        facts = [lines[i] for i in indices]
        rnd.shuffle(facts)
        for index, fact in zip(indices, facts, strict=True):
            lines[index] = fact


def _build_graph(
    size: int,
    topology: str,
    rng: random.Random,
    average_degree: int | None = None,
) -> nx.Graph:
    if size < config.MIN_GRAPH_SIZE:
        raise ValueError(f"Graph size must be at least {config.MIN_GRAPH_SIZE}")
    if topology == "erdos_renyi":
        probability = (
            config.ERDOS_RENYI_PROBABILITY
            if average_degree is None
            else min(average_degree / (size - 1), 1.0)
        )
        graph = nx.erdos_renyi_graph(size, probability, seed=rng)
    elif topology == "barabasi_albert":
        attachments = (
            config.BARABASI_ALBERT_ATTACHMENTS
            if average_degree is None
            else max(1, round(average_degree / 2))
        )
        graph = nx.barabasi_albert_graph(size, min(attachments, size - 1), seed=rng)
    elif topology == "internet_as_graph" and average_degree is not None:
        graph = _internet_as_graph(size, rng, average_degree)
    else:
        raise ValueError(f"Unknown topology: {topology}")
    _connect_components(graph)
    return graph


def _internet_as_graph(size: int, rng: random.Random, average_degree: int) -> nx.Graph:
    graph = nx.random_internet_as_graph(size, seed=rng)
    target_edges = min(
        max(size - 1, round(size * average_degree / 2)),
        size * (size - 1) // 2,
    )
    _resize_connected_graph(graph, target_edges, rng)
    return graph


def _resize_connected_graph(
    graph: nx.Graph, target_edges: int, rng: random.Random
) -> None:
    removable_edges = list(graph.edges)
    rng.shuffle(removable_edges)
    for source, target in removable_edges:
        if graph.number_of_edges() <= target_edges:
            break
        graph.remove_edge(source, target)
        if not nx.is_connected(graph):
            graph.add_edge(source, target)

    missing_edges = list(nx.non_edges(graph))
    rng.shuffle(missing_edges)
    graph.add_edges_from(missing_edges[: target_edges - graph.number_of_edges()])


def _connect_components(graph: nx.Graph) -> None:
    components = sorted(nx.connected_components(graph), key=min)
    anchor = min(components[0])
    graph.add_edges_from((anchor, min(component)) for component in components[1:])


def _number(value: float) -> str:
    return f"{value:.12g}"
