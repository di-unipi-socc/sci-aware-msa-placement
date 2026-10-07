import heapq
import random
from pathlib import Path

from sci_aware_msa_placement import config


def build_application(parameters: dict, output_dir: Path) -> tuple[Path, str]:
    rng = random.Random(parameters["seed"])
    size = parameters["application_size"]
    topology = parameters["application_topology"]
    application = f"synthetic_{topology}_{size}_{parameters['seed']}"
    services = [f"service_{index}" for index in range(size)]
    edges = _graph_edges(size, topology, rng)
    rng.shuffle(edges)

    endpoint_count = min(config.ENDPOINT_COUNT, len(edges))
    interactions = [[] for _ in range(endpoint_count)]
    for index, (source, target) in enumerate(edges):
        avg_gb = rng.uniform(*config.INTERACTION_GB_RANGE)
        interactions[index % endpoint_count].append(
            f"({services[source]},{services[target]},{_number(avg_gb)})"
        )

    weights = [rng.random() for _ in range(endpoint_count)]
    total_weight = sum(weights)
    probabilities = [weight / total_weight for weight in weights]
    endpoints = [f"endpoint_{index}" for index in range(endpoint_count)]

    lines = [
        f"application({application},[{','.join(services)}],[{','.join(endpoints)}]).",
        "",
    ]
    for service in services:
        cpu = rng.uniform(*config.CPU_REQUIREMENT_RANGE)
        ram = rng.uniform(*config.RAM_REQUIREMENT_RANGE)
        bandwidth_in = rng.uniform(*config.BANDWIDTH_REQUIREMENT_RANGE)
        bandwidth_out = rng.uniform(*config.BANDWIDTH_REQUIREMENT_RANGE)
        time_in_reserve = rng.uniform(*config.TIME_IN_RESERVE_RANGE)
        lines.append(
            f"microservice({service},rr({_number(cpu)},{_number(ram)},"
            f"{_number(bandwidth_in)},{_number(bandwidth_out)}),"
            f"{_number(time_in_reserve)})."
        )

    lines.append("")
    for endpoint, pairs, probability in zip(
        endpoints, interactions, probabilities, strict=True
    ):
        lines.append(f"endpoint({endpoint},[{','.join(pairs)}]).")
        lines.append(f"probability({endpoint},{_number(probability)}).")

    lines.extend(["", f"functionalUnits({application},{config.FUNCTIONAL_UNITS})."])
    path = output_dir / "application.pl"
    path.write_text("\n".join(lines) + "\n", encoding=config.ENCODING)
    return path, application


def build_network(parameters: dict, output_dir: Path) -> Path:
    rng = random.Random(parameters["seed"] + 1)
    size = parameters["infrastructure_size"]
    topology = parameters["infrastructure_topology"]
    profile = parameters["route_profile"]
    embodied_per_gb = (
        profile["embodied_per_gb"]
        if parameters["include_network_embodied"]
        else 0.0
    )
    nodes = [f"node_{index}" for index in range(size)]
    edges = _graph_edges(size, topology, rng)
    weighted_edges = [
        (source, target, rng.uniform(*config.LINK_DISTANCE_KM_RANGE))
        for source, target in edges
    ]

    lines = []
    for node in nodes:
        cpu = rng.randint(*config.NODE_CPU_RANGE)
        ram = rng.uniform(*config.NODE_RAM_RANGE)
        bandwidth_in = rng.uniform(*config.NODE_BANDWIDTH_RANGE)
        bandwidth_out = rng.uniform(*config.NODE_BANDWIDTH_RANGE)
        power = rng.uniform(*config.POWER_PER_CPU_RANGE)
        lifetime = rng.uniform(*config.EXPECTED_LIFETIME_RANGE)
        embodied = rng.uniform(*config.TOTAL_EMBODIED_EMISSIONS_RANGE)
        pue = rng.uniform(*config.PUE_RANGE)
        carbon_intensity = rng.uniform(*config.CARBON_INTENSITY_RANGE)
        lines.append(
            f"node({node},tor({cpu},{_number(ram)},{_number(bandwidth_in)},"
            f"{_number(bandwidth_out)}),{_number(power)},{_number(lifetime)},"
            f"{_number(embodied)},{_number(pue)})."
        )
        lines.append(f"carbon_intensity({node},{_number(carbon_intensity)}).")

    lines.extend(
        [
            "",
            f"routeProfile({profile['name']},{profile['operational_per_gb']},"
            f"{embodied_per_gb}).",
            "",
        ]
    )
    distances = _shortest_distances(size, weighted_edges)
    for source in range(size):
        for target in range(size):
            if source != target:
                lines.append(
                    f"route({nodes[source]},{nodes[target]},"
                    f"{_number(distances[source][target])},{profile['name']})."
                )

    path = output_dir / "infrastructure.pl"
    path.write_text("\n".join(lines) + "\n", encoding=config.ENCODING)
    return path


def _graph_edges(size: int, topology: str, rng: random.Random) -> list[tuple[int, int]]:
    if size < 2:
        raise ValueError("Graph size must be at least 2")
    if topology == "erdos_renyi":
        edges = _erdos_renyi(size, rng)
    elif topology == "barabasi_albert":
        edges = _barabasi_albert(size, rng)
    elif topology == "watts_strogatz":
        edges = _watts_strogatz(size, rng)
    else:
        raise ValueError(f"Unknown topology: {topology}")
    return sorted(_connect_components(size, edges))


def _erdos_renyi(size: int, rng: random.Random) -> set[tuple[int, int]]:
    return {
        (source, target)
        for source in range(size)
        for target in range(source + 1, size)
        if rng.random() < config.ERDOS_RENYI_PROBABILITY
    }


def _barabasi_albert(size: int, rng: random.Random) -> set[tuple[int, int]]:
    attachments = min(config.BARABASI_ALBERT_ATTACHMENTS, size - 1)
    initial_size = attachments + 1
    edges = {
        (source, target)
        for source in range(initial_size)
        for target in range(source + 1, initial_size)
    }
    degrees = [initial_size - 1] * initial_size
    for node in range(initial_size, size):
        targets = set()
        while len(targets) < attachments:
            targets.add(rng.choices(range(node), weights=degrees, k=1)[0])
        degrees.append(0)
        for target in targets:
            edges.add((target, node))
            degrees[target] += 1
            degrees[node] += 1
    return edges


def _watts_strogatz(size: int, rng: random.Random) -> set[tuple[int, int]]:
    neighbors = min(config.WATTS_STROGATZ_NEIGHBORS, size - 1)
    neighbors -= neighbors % 2
    edges = set()
    for source in range(size):
        for offset in range(1, neighbors // 2 + 1):
            target = (source + offset) % size
            edge = tuple(sorted((source, target)))
            if rng.random() < config.WATTS_STROGATZ_REWIRE_PROBABILITY:
                candidates = [
                    node
                    for node in range(size)
                    if node != source and tuple(sorted((source, node))) not in edges
                ]
                if candidates:
                    edge = tuple(sorted((source, rng.choice(candidates))))
            edges.add(edge)
    return edges


def _connect_components(
    size: int, edges: set[tuple[int, int]]
) -> set[tuple[int, int]]:
    connected = {0}
    while len(connected) < size:
        expanded = connected | {
            target for source, target in edges if source in connected
        } | {source for source, target in edges if target in connected}
        if expanded == connected:
            target = min(set(range(size)) - connected)
            edges.add((min(connected), target))
            expanded.add(target)
        connected = expanded
    return edges


def _shortest_distances(
    size: int, edges: list[tuple[int, int, float]]
) -> list[list[float]]:
    adjacency = [[] for _ in range(size)]
    for source, target, distance in edges:
        adjacency[source].append((target, distance))
        adjacency[target].append((source, distance))

    distances = []
    for origin in range(size):
        current = [float("inf")] * size
        current[origin] = 0.0
        queue = [(0.0, origin)]
        while queue:
            distance, node = heapq.heappop(queue)
            if distance != current[node]:
                continue
            for neighbor, weight in adjacency[node]:
                candidate = distance + weight
                if candidate < current[neighbor]:
                    current[neighbor] = candidate
                    heapq.heappush(queue, (candidate, neighbor))
        distances.append(current)
    return distances


def _number(value: float) -> str:
    return f"{value:.12g}"
