from model import Drone, Zone, Connection, Graph

from collections import Counter


class Simulation:
    """Manage drones and advance the simulation turn by turn."""

    def __init__(self, graph: Graph, drones: list[Drone]) -> None:
        self.graph = graph
        self.drones = drones
        self.turn = 0

    def check_zone_capacity(
        self,
        drone: Drone,
        next_zone: Zone,
    ) -> bool:
        """Check whether a drone can enter the next zone."""
        count = 0
        for drone in self.drones:
            if drone.current_zone == next_zone:
                count += 1
        return count + 1 <= next_zone.max_drones

    def check_connection_capacity(
        self,
        from_zone: Zone,
        to_zone: Zone,
        count: int,
    ) -> bool:
        """Check whether the connection has capacity for the proposed moves."""
        conn = self.graph.get_connection(from_zone, to_zone)

        if conn is None:
            return False

        return count <= conn.max_link_capacity

    def next_moved_list(self) -> dict[int, Zone]:
        next_moves: dict[int, Zone] = {}

        for drone in self.drones:
            if (
                drone.path
                and drone.current_zone == drone.path[drone.path_index]
                and drone.path_index + 1 < len(drone.path)
            ):
                next_zone: Zone = drone.path[drone.path_index + 1]
                next_moves[drone.drone_id] = next_zone

        return next_moves

    def count_connection_usage(self) -> Counter[tuple[str, str]]:
        next_moves: dict[int, Zone] = self.next_moved_list()
        connections: list[tuple[str, str]] = []
        for drone_id, next_zone in next_moves.items():
            for drone in self.drones:
                if drone.drone_id == drone_id:
                    current_zone = drone.current_zone
            # Bidirectional connection - sorted
            if self.graph.get_connection(current_zone, next_zone):
                connections.append(tuple(sorted((current_zone.name, next_zone.name))))
        return Counter(connections)

    def validate_connection_usage(self) -> bool:
        count_connection: dict[tuple[str, str], int] = self.count_connection_usage()

        for (from_zone, to_zone), count in count_connection.items():

            from_zone_obj = self.graph.get_zone(from_zone)
            to_zone_obj = self.graph.get_zone(to_zone)

            if from_zone_obj is None or to_zone_obj is None:
                return False
            if not self.check_connection_capacity(
                from_zone_obj,
                to_zone_obj,
                count,
            ):
                return False
        return True
