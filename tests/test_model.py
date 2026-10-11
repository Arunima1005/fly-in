from src.model import Connection, Graph, Zone


def test_get_neighbors() -> None:
    zone_a = Zone(name="A", x=0, y=0)
    zone_b = Zone(name="B", x=1, y=0)
    zone_c = Zone(name="C", x=2, y=0)

    graph = Graph()

    graph.add_zone(zone_a)
    graph.add_zone(zone_b)
    graph.add_zone(zone_c)

    graph.add_connection(Connection(zone_a=zone_a, zone_b=zone_b))
    graph.add_connection(Connection(zone_a=zone_b, zone_b=zone_c))

    neighbors_a = graph.get_neighbors(zone_a)
    neighbors_b = graph.get_neighbors(zone_b)
    neighbors_c = graph.get_neighbors(zone_c)

    assert [zone.name for zone in neighbors_a] == ["B"]
    assert [zone.name for zone in neighbors_b] == ["A", "C"]
    assert [zone.name for zone in neighbors_c] == ["B"]
