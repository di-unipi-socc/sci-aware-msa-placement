import random
import re
from functools import cache
from pathlib import Path

import networkx as nx

from sci_aware_msa_placement import config


def build_application(
    parameters: dict, output_dir: Path
) -> tuple[Path, str, dict]:
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
            endpoint_interactions.append(
                f"({source},{target},{_number(avg_gb)})"
            )
            endpoint_volumes.append(avg_gb)
        interactions.append(endpoint_interactions)
        interaction_volumes.append(endpoint_volumes)

    lines = [
        f"application({application},[{','.join(services)}],[{','.join(endpoints)}]).",
        "",
    ]
    cpu_requirements, ram_requirements = _incomparable_requirements(
        requirements_rng, len(services)
    )
    service_requirements = {}
    for service, cpu, ram in zip(
        services, cpu_requirements, ram_requirements, strict=True
    ):
        bandwidth_in = requirements_rng.uniform(*config.BANDWIDTH_REQUIREMENT_RANGE)
        bandwidth_out = requirements_rng.uniform(*config.BANDWIDTH_REQUIREMENT_RANGE)
        time_in_reserve = requirements_rng.uniform(*config.TIME_IN_RESERVE_RANGE)
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

    endpoint_lines = []
    probability_lines = []
    for endpoint, pairs, probability in zip(
        endpoints, interactions, probabilities, strict=True
    ):
        endpoint_lines.append(f"endpoint({endpoint},[{','.join(pairs)}]).")
        probability_lines.append(
            f"probability({endpoint},{_number(probability)})."
        )

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
) -> tuple[Path, dict]:
    seed = parameters["seed"]
    graph_rng = random.Random(seed + 4_000_000)
    size = parameters["infrastructure_size"]
    graph = parameters["infrastructure_graph"]
    topology = graph["topology"]
    average_degree = config.AVERAGE_DEGREE_BY_DENSITY[
        graph["density"]
    ]
    route_profile = parameters["route_profile"]
    embodied_per_gb = (
        route_profile["embodied_per_gb"]
        if parameters["include_network_embodied"]
        else 0.0
    )
    nodes = [f"node_{index}" for index in range(size)]
    services = list(service_requirements)
    fit_node_count = len(services)
    if size < fit_node_count + 2:
        raise ValueError("Controlled infrastructure needs fit, dirty, and broken nodes")
    extra_node_count = size - fit_node_count
    dirty_node_count = (extra_node_count + 1) // 2
    long_link_km = max(
        config.CONTROLLED_LONG_LINK_KM,
        config.CONTROLLED_SHORT_LINK_KM * fit_node_count + 1,
    )
    network = _build_graph(size, topology, graph_rng, average_degree)
    network.add_edges_from((index, index + 1) for index in range(fit_node_count - 1))
    for source, target in network.edges:
        network[source][target]["distance"] = (
            config.CONTROLLED_SHORT_LINK_KM
            if source < fit_node_count and target < fit_node_count
            else long_link_km
        )

    node_lines = []
    carbon_intensity_lines = []
    fit_nodes = []
    for index, node in enumerate(nodes):
        if index < fit_node_count:
            service = services[index]
            cpu, ram, bandwidth_in, bandwidth_out = service_requirements[service]
            profile = config.CONTROLLED_FIT_PROFILE
            fit_nodes.append((service, node))
        elif index < fit_node_count + dirty_node_count:
            service_index = (index - fit_node_count) % fit_node_count
            cpu, ram, bandwidth_in, bandwidth_out = service_requirements[
                services[service_index]
            ]
            profile = config.CONTROLLED_DIRTY_PROFILE
        else:
            cpu = ram = bandwidth_in = bandwidth_out = 0
            profile = config.CONTROLLED_DIRTY_PROFILE

        power = profile["power_per_cpu"]
        lifetime = profile["expected_lifetime"]
        embodied = profile["embodied_emissions_per_cpu"] * cpu
        pue = profile["pue"]
        carbon_intensity = profile["carbon_intensity"]
        node_lines.append(
            f"node({node},tor({_number(cpu)},{_number(ram)},{_number(bandwidth_in)},"
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
        "",
        *(
            f"fitNode({application},{service},{node})."
            for service, node in fit_nodes
        ),
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
    distances = dict(
        nx.all_pairs_dijkstra_path_length(network, weight="distance")
    )
    for source in range(size):
        for target in range(size):
            if source != target:
                lines.append(
                    f"route({nodes[source]},{nodes[target]},"
                    f"{_number(distances[source][target])},"
                    f"{route_profile['name']})."
                )

    path = output_dir / "infrastructure.pl"
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
            sum(
                attributes["distance"]
                for _, _, attributes in network.edges(data=True)
            )
            / network.number_of_edges()
        ),
        "average_route_distance_km": sum(route_distances) / len(route_distances),
        "maximum_route_distance_km": max(route_distances),
    }
    return path, metadata


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
        graph = nx.barabasi_albert_graph(
            size, min(attachments, size - 1), seed=rng
        )
    elif topology == "internet_as_graph" and average_degree is not None:
        graph = _internet_as_graph(size, rng, average_degree)
    else:
        raise ValueError(f"Unknown topology: {topology}")
    _connect_components(graph)
    return graph


def _internet_as_graph(
    size: int, rng: random.Random, average_degree: int
) -> nx.Graph:
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
    graph.add_edges_from(
        missing_edges[: target_edges - graph.number_of_edges()]
    )


def _connect_components(graph: nx.Graph) -> None:
    components = sorted(nx.connected_components(graph), key=min)
    anchor = min(components[0])
    graph.add_edges_from((anchor, min(component)) for component in components[1:])


def _number(value: float) -> str:
    return f"{value:.12g}"
