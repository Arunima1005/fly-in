from .dijkstra import Dijkstra
from .model import Drone, Zone, Connection, Graph, ZoneType

from collections import Counter


class Simulation:
    """Manage drones and advance the simulation turn by turn."""

    def __init__(self, graph: Graph, drones: list[Drone], end_zone: Zone, start_zone: Zone,) -> None:
        self.graph = graph
        self.drones = drones
        self.turn = 0
        self.end_zone = end_zone
        self.start_zone = start_zone

        
    def assign_paths(self) -> None:
        """Calculate and assign a path to every drone."""
        dijkstra = Dijkstra(self.graph)
        zone_usage: Counter[str] = Counter()
        for drone in self.drones:
            path: list[Zone] = dijkstra.find_path(
                        self.start_zone,
                        self.end_zone,
                        zone_usage,
                    )
            if path is None:
                raise ValueError("No path found from start to end")
            drone.path = path
            drone.path_index = 0
            for zone in path:
                zone_usage[zone.name] += 1

    def check_zone_capacity(
        self,
        drone: Drone,
        next_zone: Zone,
        zone_usage: Counter[str],
        departures: Counter[str],
    ) -> bool:
        """Check whether a drone can enter the next zone."""
        if next_zone == self.end_zone:
            return True
        count = 0
        for drone in self.drones:
            if drone.current_zone == next_zone:
                count += 1
        return (
            count
            - departures[next_zone.name]
            + zone_usage[next_zone.name]
            + 1
            <= next_zone.max_drones
        )

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
            if drone.movement_remaining > 0:
                continue
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

    def filter_connection_moves(
    self,
    next_moves: dict[int, Zone],
) -> dict[int, Zone]:
        """Keep moves that respect connection capacity."""
        valid_move: dict[int, Zone] = {}
        connection_usage: Counter[tuple[str, str]] = Counter()
        zone_usage: Counter[str] = Counter()
        departures = self.count_zone_departures(next_moves)
        
        for drone_id, next_zone in next_moves.items():
            for drone in self.drones:
                if drone.drone_id == drone_id:
                    current_zone = drone.current_zone

                    connection_key = tuple(
                        sorted((current_zone.name, next_zone.name))
                    )

                    current_usage = connection_usage[connection_key]
                    connection = self.graph.get_connection(current_zone, next_zone,)
                    if connection is None:
                        continue
                    if current_usage + 1 <= connection.max_link_capacity and self.check_zone_capacity(drone, next_zone, zone_usage, departures,):
                        valid_move[drone_id] = next_zone
                        connection_usage[connection_key] += 1
                        zone_usage[next_zone.name] += 1
        return valid_move

    def apply_moves(self, valid_moves: dict[int, Zone]) -> None:
        """Apply the accepted drone moves."""

        for drone_id, next_zone in valid_moves.items():
            for drone in self.drones:
                if drone.drone_id == drone_id:
                    if next_zone.zone_type == ZoneType.RESTRICTED:
                        drone.movement_remaining = 1
                    else:
                        drone.current_zone = next_zone
                        drone.path_index += 1

    def run_turn(self) -> bool:
        """Execute one simulation turn."""
        moved_drones: set[int] = set()
        moved = False

        for drone in self.drones:
            if drone.movement_remaining > 0:
                drone.current_zone = drone.path[drone.path_index + 1]
                drone.path_index += 1
                drone.movement_remaining = 0
                moved = True
                moved_drones.add(drone.drone_id)
        next_moves = self.next_moved_list()
        for drone_id in moved_drones:
            next_moves.pop(drone_id, None)
        valid_moves = self.filter_connection_moves(next_moves)

        if valid_moves:
            self.apply_moves(valid_moves)
            moved = True

        if moved:
            self.turn += 1

        return moved

    def all_drones_finished(self) -> bool:
        """Return True when all drones have reached the end zone."""
        return all(drone.current_zone == self.end_zone for drone in self.drones)

    def run(self) -> None:
        """Run the simulation until all drones reach the end."""
        self.assign_paths()
        while not self.all_drones_finished():
            moved = self.run_turn()

            if not moved:
                break
            self.print_status()

    def print_status(self) -> None:
        """Print the current position of every drone."""
        positions = []

        for drone in self.drones:
            positions.append(
                f"D{drone.drone_id}={drone.current_zone.name}"
            )

        print(f"Turn {self.turn}: {', '.join(positions)}")


    def count_zone_departures(
    self,
    next_moves: dict[int, Zone],
) -> Counter[str]:
        """Count drones leaving each zone during this turn."""
        departures: Counter[str] = Counter()

        for drone_id in next_moves:
            for drone in self.drones:
                if drone.drone_id == drone_id:
                    departures[drone.current_zone.name] += 1
                    break

        return departures