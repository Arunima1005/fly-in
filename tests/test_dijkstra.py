import pytest

from src.model import Graph, Zone, ZoneType, Connection
from dijkstra_old import Dijkstra


def create_zone(name: str, zone_type: ZoneType = ZoneType.NORMAL) -> Zone:
    return Zone(
        name=name,
        x=0,
        y=0,
        zone_type=zone_type,
    )


def create_graph(
    zones: list[Zone],
    connections: list[tuple[str, str]],
) -> Graph:
    zone_dict = {zone.name: zone for zone in zones}

    graph_connections = [
        Connection(
            zone_a=zone_dict[a],
            zone_b=zone_dict[b],
        )
        for a, b in connections
    ]

    return Graph(
        zones=zone_dict,
        connections=graph_connections,
    )


def test_simple_path() -> None:
    """Find a path through a simple linear graph."""
    a = create_zone("A")
    b = create_zone("B")
    c = create_zone("C")

    graph = create_graph(
        [a, b, c],
        [("A", "B"), ("B", "C")],
    )

    dijkstra = Dijkstra(graph)
    path = dijkstra.find_path(a, c)

    assert path is not None
    assert [zone.name for zone in path] == ["A", "B", "C"]


def test_restricted_zone_cost() -> None:
    """Prefer a longer route when it has a lower movement cost."""
    a = create_zone("A")
    b = create_zone("B", ZoneType.RESTRICTED)
    c = create_zone("C")
    d = create_zone("D")

    graph = create_graph(
        [a, b, c, d],
        [
            ("A", "B"),
            ("B", "D"),
            ("A", "C"),
            ("C", "D"),
        ],
    )

    dijkstra = Dijkstra(graph)
    path = dijkstra.find_path(a, d)

    assert path is not None
    assert [zone.name for zone in path] == ["A", "C", "D"]


def test_blocked_zone_is_avoided() -> None:
    """Do not enter a blocked zone if another route exists."""
    a = create_zone("A")
    b = create_zone("B", ZoneType.BLOCKED)
    c = create_zone("C")
    d = create_zone("D")

    graph = create_graph(
        [a, b, c, d],
        [
            ("A", "B"),
            ("B", "D"),
            ("A", "C"),
            ("C", "D"),
        ],
    )

    dijkstra = Dijkstra(graph)
    path = dijkstra.find_path(a, d)

    assert path is not None
    assert [zone.name for zone in path] == ["A", "C", "D"]


def test_unreachable_destination() -> None:
    """Return None when the destination cannot be reached."""
    a = create_zone("A")
    b = create_zone("B")
    c = create_zone("C")

    graph = create_graph(
        [a, b, c],
        [("A", "B")],
    )

    dijkstra = Dijkstra(graph)
    path = dijkstra.find_path(a, c)

    assert path is None


def test_start_equals_end() -> None:
    """Return a path containing only the start zone."""
    a = create_zone("A")
    b = create_zone("B")

    graph = create_graph(
        [a, b],
        [("A", "B")],
    )

    dijkstra = Dijkstra(graph)
    path = dijkstra.find_path(a, a)

    assert path is not None
    assert [zone.name for zone in path] == ["A"]


def test_choose_cheapest_route() -> None:
    """Choose the route with the lowest total movement cost."""
    a = create_zone("A")
    b = create_zone("B")
    c = create_zone("C")
    d = create_zone("D")
    e = create_zone("E")

    graph = create_graph(
        [a, b, c, d, e],
        [
            ("A", "B"),
            ("B", "D"),
            ("A", "C"),
            ("C", "E"),
            ("E", "D"),
        ],
    )

    dijkstra = Dijkstra(graph)
    path = dijkstra.find_path(a, d)

    assert path is not None
    assert [zone.name for zone in path] == ["A", "B", "D"]



def test_blocked_start() -> None:
    """Do not enter a blocked zone if another route exists."""
    a = create_zone("A", ZoneType.BLOCKED)
    b = create_zone("B", ZoneType.BLOCKED)
    c = create_zone("C", ZoneType.BLOCKED)
    d = create_zone("D", ZoneType.BLOCKED)

    graph = create_graph(
        [a, b, c, d],
        [
            ("A", "B"),
            ("B", "D"),
            ("A", "C"),
            ("C", "D"),
        ],
    )

    dijkstra = Dijkstra(graph)
    path = dijkstra.find_path(a, d)

    assert path is None


def test_blocked_destination() -> None:
    """Do not enter a blocked zone if another route exists."""
    a = create_zone("A")
    b = create_zone("B", ZoneType.BLOCKED)
    c = create_zone("C", ZoneType.BLOCKED)
    d = create_zone("D", ZoneType.BLOCKED)

    graph = create_graph(
        [a, b, c, d],
        [
            ("A", "B"),
            ("B", "D"),
            ("A", "C"),
            ("C", "D"),
        ],
    )

    dijkstra = Dijkstra(graph)
    path = dijkstra.find_path(a, d)

    assert path is None

def test_prefer_priority_zone_when_costs_tie() -> None:
    """Prefer a route with more priority zones when costs are equal."""
    a = create_zone("A")
    b = create_zone("B", ZoneType.PRIORITY)
    c = create_zone("C")
    d = create_zone("D")

    graph = create_graph(
        [a, b, c, d],
        [
            ("A", "B"),
            ("B", "D"),
            ("A", "C"),
            ("C", "D"),
        ],
    )

    dijkstra = Dijkstra(graph)
    path = dijkstra.find_path(a, d)

    assert path is not None
    assert [zone.name for zone in path] == ["A", "B", "D"]


def test_prefer_more_priority_zones() -> None:
    """Prefer more priority zones when route costs tie."""
    a = create_zone("A")
    b = create_zone("B", ZoneType.PRIORITY)
    c = create_zone("C")
    d = create_zone("D", ZoneType.PRIORITY)
    e = create_zone("E", ZoneType.PRIORITY)
    f = create_zone("F")

    graph = create_graph(
        [a, b, c, d, e, f],
        [
            ("A", "B"),
            ("B", "C"),
            ("C", "F"),
            ("A", "D"),
            ("D", "E"),
            ("E", "F"),
        ],
    )

    dijkstra = Dijkstra(graph)
    path = dijkstra.find_path(a, f)

    assert path is not None
    assert [zone.name for zone in path] == ["A", "D", "E", "F"]

def test_cost_has_priority_over_priority_count() -> None:
    """Prefer lower cost over a route with more priority zones."""
    a = create_zone("A")
    b = create_zone("B", ZoneType.PRIORITY)
    c = create_zone("C", ZoneType.PRIORITY)
    d = create_zone("D")
    e = create_zone("E")

    graph = create_graph(
        [a, b, c, d, e],
        [
            ("A", "B"),
            ("B", "C"),
            ("C", "D"),
            ("A", "E"),
            ("E", "D"),
        ],
    )

    graph.zones["B"].zone_type = ZoneType.RESTRICTED
    graph.zones["C"].zone_type = ZoneType.PRIORITY

    dijkstra = Dijkstra(graph)
    path = dijkstra.find_path(a, d)

    assert path is not None
    assert [zone.name for zone in path] == ["A", "E", "D"]

def test_no_path_through_blocked_zones() -> None:
    """Return None if every possible route is blocked."""
    a = create_zone("A")
    b = create_zone("B", ZoneType.BLOCKED)
    c = create_zone("C", ZoneType.BLOCKED)
    d = create_zone("D")

    graph = create_graph(
        [a, b, c, d],
        [
            ("A", "B"),
            ("B", "D"),
            ("A", "C"),
            ("C", "D"),
        ],
    )

    dijkstra = Dijkstra(graph)
    path = dijkstra.find_path(a, d)

    assert path is None


def test_get_connection() -> None:
    a = Zone(name="A", x=0, y=0)
    b = Zone(name="B", x=1, y=0)
    connection = Connection(
        zone_a=a,
        zone_b=b,
        max_link_capacity=2,
    )
    graph = Graph(
        zones={"A": a, "B": b},
        connections=[connection],
    )

    assert graph.get_connection(a, b) == connection


def test_get_connection_is_bidirectional() -> None:
    a = Zone(name="A", x=0, y=0)
    b = Zone(name="B", x=1, y=0)
    connection = Connection(zone_a=a, zone_b=b)
    graph = Graph(
        zones={"A": a, "B": b},
        connections=[connection],
    )

    assert graph.get_connection(b, a) == connection


def test_get_connection_not_found() -> None:
    a = Zone(name="A", x=0, y=0)
    b = Zone(name="B", x=1, y=0)
    c = Zone(name="C", x=2, y=0)
    graph = Graph(
        zones={"A": a, "B": b, "C": c},
        connections=[Connection(zone_a=a, zone_b=b)],
    )

    assert graph.get_connection(a, c) is None