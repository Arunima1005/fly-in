from model import Connection, Graph, GraphError, Zone


class ReservationTable:
    """Track zone and connection usage per turn for already-planned drones."""

    def __init__(self, graph: Graph) -> None:
        if graph.start_zone is None or graph.end_zone is None:
            raise GraphError("graph needs a start and an end zone")
        self._graph = graph
        self._unlimited: set[str] = {graph.start_zone.name,
                                     graph.end_zone.name}
        self._zone_use: dict[tuple[str, int], int] = {}
        self._link_use: dict[tuple[tuple[str, str], int], int] = {}

    @staticmethod
    def link_key(connection: Connection) -> tuple[str, str]:
        """Return an order-independent key for a connection."""
        a = connection.zone_src.name
        b = connection.zone_dest.name
        return (a, b) if a < b else (b, a)

    def zone_has_room(self, zone: Zone, turn: int) -> bool:
        """True if one more drone can be in this zone at the end of turn."""
        if zone.name in self._unlimited:
            return True
        used = self._zone_use.get((zone.name, turn), 0)
        return used < zone.max_drones

    def link_has_room(self, connection: Connection, turn: int) -> bool:
        """True if one more drone can travel this connection during turn."""
        used = self._link_use.get((self.link_key(connection), turn), 0)
        return used < connection.max_link_capacity

    def commit(self, path: list[Zone | Connection]) -> None:
        """Record everything a planned drone uses; path[t] = position at t."""
        for turn in range(1, len(path)):
            prev, cur = path[turn - 1], path[turn]
            if isinstance(cur, Connection):
                # first turn of a restricted transit: on the link, no zone
                self._use_link(cur, turn)
            elif isinstance(prev, Connection):
                # second turn: still on the link, then arrives in the zone
                self._use_link(prev, turn)
                self._use_zone(cur, turn)
            else:
                if prev.name != cur.name:
                    conn = self._graph.get_connection(prev.name, cur.name)
                    if conn is None:
                        raise GraphError(
                            f"no connection {prev.name}-{cur.name}")
                    self._use_link(conn, turn)
                self._use_zone(cur, turn)  # also covers waiting

    def _use_zone(self, zone: Zone, turn: int) -> None:
        if zone.name in self._unlimited:
            return
        key = (zone.name, turn)
        self._zone_use[key] = self._zone_use.get(key, 0) + 1

    def _use_link(self, connection: Connection, turn: int) -> None:
        key = (self.link_key(connection), turn)
        self._link_use[key] = self._link_use.get(key, 0) + 1