from .dijkstra import Dijkstra
from .model import Drone, Zone, Graph, ZoneType

import sys
from collections import Counter

# Terminal colors
RESET = "\033[0m"
BOLD = "\033[1m"

CYAN = "\033[96m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RED = "\033[91m"
WHITE = "\033[97m"
MAGENTA = "\033[95m"


class Simulation:
    """Manage drones and advance the simulation turn by turn."""

    def __init__(
        self,
        graph: Graph,
        drones: list[Drone],
        end_zone: Zone,
        start_zone: Zone,
        verbose: bool = False,
    ) -> None:
        """Set up the drones, the graph and the turn counter."""
        self.graph = graph
        self.drones = drones
        self.turn = 0
        self.end_zone = end_zone
        self.start_zone = start_zone
        self.verbose = verbose
        # Moves made during the last turn as (drone, zone, label), where
        # label is the zone name or, for a drone taking off toward a
        # restricted zone, the connection name.
        self.turn_moves: list[tuple[Drone, Zone, str]] = []

    def assign_paths(self) -> None:
        """Calculate and assign a path to every drone."""
        dijkstra = Dijkstra(self.graph)
        zone_usage: Counter[str] = Counter()
        for drone in self.drones:
            path: list[Zone] | None = dijkstra.find_path(
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

    def is_unlimited(self, zone: Zone) -> bool:
        """Return True for zones without a capacity limit (start and end)."""
        return zone == self.start_zone or zone == self.end_zone

    def occupied_zone(self, drone: Drone) -> Zone:
        """Return the zone a drone counts against for capacity.

        A drone flying toward a restricted zone has already left its
        origin and has a reserved spot in its destination, so it is
        guaranteed to be able to land on the next turn.
        """
        if drone.movement_remaining > 0:
            return drone.path[drone.path_index + 1]
        return drone.current_zone

    def connection_key(self, zone_a: Zone, zone_b: Zone) -> tuple[str, str]:
        """Return an order-independent key for a connection."""
        if zone_a.name <= zone_b.name:
            return (zone_a.name, zone_b.name)
        return (zone_b.name, zone_a.name)

    def next_moved_list(self) -> dict[int, Zone]:
        """Return the next zone each grounded drone wants to move to."""
        next_moves: dict[int, Zone] = {}

        for drone in self.drones:
            if drone.movement_remaining > 0:
                continue
            if drone.path and drone.path_index + 1 < len(drone.path):
                next_moves[drone.drone_id] = drone.path[drone.path_index + 1]

        return next_moves

    def select_moves(
        self,
        next_moves: dict[int, Zone],
        occupancy: Counter[str],
        link_usage: Counter[tuple[str, str]],
    ) -> dict[int, Zone]:
        """Choose which requested moves can happen this turn.

        A zone only gains free space when a drone really leaves it, so
        moves are accepted one at a time and the occupancy is updated
        after each one. Passes repeat until nothing changes, which lets
        a drone follow another one that was accepted later in the pass.
        Drones furthest along their path go first to clear the way.
        """
        drones_by_id = {drone.drone_id: drone for drone in self.drones}
        pending = sorted(
            next_moves,
            key=lambda drone_id: -drones_by_id[drone_id].path_index,
        )
        accepted: dict[int, Zone] = {}

        changed = True
        while changed:
            changed = False
            for drone_id in list(pending):
                drone = drones_by_id[drone_id]
                next_zone = next_moves[drone_id]
                connection = self.graph.get_connection(
                    drone.current_zone,
                    next_zone,
                )
                if connection is None:
                    pending.remove(drone_id)
                    continue

                key = self.connection_key(drone.current_zone, next_zone)
                if link_usage[key] + 1 > connection.max_link_capacity:
                    continue
                if (
                    not self.is_unlimited(next_zone)
                    and occupancy[next_zone.name] + 1 > next_zone.max_drones
                ):
                    continue

                accepted[drone_id] = next_zone
                pending.remove(drone_id)
                link_usage[key] += 1
                occupancy[drone.current_zone.name] -= 1
                occupancy[next_zone.name] += 1
                changed = True

        return accepted

    def apply_moves(self, valid_moves: dict[int, Zone]) -> None:
        """Apply the accepted drone moves."""
        for drone in self.drones:
            next_zone = valid_moves.get(drone.drone_id)
            if next_zone is None:
                continue
            if next_zone.zone_type == ZoneType.RESTRICTED:
                drone.movement_remaining = 1
                label = f"{drone.current_zone.name}-{next_zone.name}"
            else:
                drone.current_zone = next_zone
                drone.path_index += 1
                label = next_zone.name
            self.turn_moves.append((drone, next_zone, label))

    def run_turn(self) -> bool:
        """Execute one simulation turn."""
        occupancy: Counter[str] = Counter(
            self.occupied_zone(drone).name for drone in self.drones
        )
        link_usage: Counter[tuple[str, str]] = Counter()
        landed: set[int] = set()
        moved = False
        self.turn_moves = []

        # Drones in flight must land now. Their destination spot was
        # reserved at take-off, but they still use the connection for
        # this turn, so it counts against the link capacity.
        for drone in self.drones:
            if drone.movement_remaining > 0:
                destination = drone.path[drone.path_index + 1]
                key = self.connection_key(drone.current_zone, destination)
                link_usage[key] += 1
                drone.current_zone = destination
                drone.path_index += 1
                drone.movement_remaining = 0
                landed.add(drone.drone_id)
                self.turn_moves.append((drone, destination, destination.name))
                moved = True

        # A drone that just landed has used its move for this turn.
        next_moves = self.next_moved_list()
        for drone_id in landed:
            next_moves.pop(drone_id, None)
        valid_moves = self.select_moves(next_moves, occupancy, link_usage)

        if valid_moves:
            self.apply_moves(valid_moves)
            moved = True

        if moved:
            self.turn += 1

        return moved

    def all_drones_finished(self) -> bool:
        """Return True when all drones have reached the end zone."""
        return all(
            drone.current_zone == self.end_zone for drone in self.drones
        )

    def run(self) -> None:
        """Run the simulation until all drones reach the end."""

        self.assign_paths()
        if self.verbose:
            self.print_header()

        while not self.all_drones_finished():
            moved = self.run_turn()

            if not moved:
                print(
                    f"{RED}Simulation stopped: no drones can move.{RESET}",
                    file=sys.stderr,
                )
                return

            self.print_turn()

        if self.verbose:
            self.print_summary()

    def print_turn(self) -> None:
        """Print the last turn: detailed with --verbose, plain otherwise."""
        if self.verbose:
            self.print_status()
        else:
            self.print_moves()

    def print_moves(self) -> None:
        """Print the movements from the last turn."""

        moves = []

        for drone, zone, label in sorted(
            self.turn_moves,
            key=lambda move: move[0].drone_id,
        ):
            moves.append(f"D{drone.drone_id}-{label}")

        print(" ".join(moves))

    def print_header(self) -> None:
        """Print the simulation header."""

        print()
        print(f"{CYAN}{'=' * 60}{RESET}")
        print(f"{BOLD}{CYAN}              FLY-IN - DRONE SIMULATION{RESET}")
        print(f"{CYAN}{'=' * 60}{RESET}")
        print()

        print(f"{BOLD}{CYAN}SIMULATION INFO{RESET}")
        print(f"{GREEN}✓ Drones : {len(self.drones)}{RESET}")
        print(f"{GREEN}✓ Start  : {self.start_zone.name}{RESET}")
        print(f"{GREEN}✓ End    : {self.end_zone.name}{RESET}")
        print()

        print(f"{CYAN}{'-' * 60}{RESET}")
        print(f"{BOLD}{CYAN}                    SIMULATION{RESET}")
        print(f"{CYAN}{'-' * 60}{RESET}")

    def print_status(self) -> None:
        """Print the current position of every drone."""

        positions = []

        for drone in self.drones:
            if drone.movement_remaining > 0:
                destination = drone.path[drone.path_index + 1]
                positions.append(
                    f"{RED}D{drone.drone_id}-"
                    f"{drone.current_zone.name}-{destination.name}{RESET}"
                )
            elif drone.current_zone == self.end_zone:
                positions.append(
                    f"{GREEN}D{drone.drone_id}-"
                    f"{drone.current_zone.name}{RESET}"
                )
            elif drone.current_zone == self.start_zone:
                positions.append(
                    f"{MAGENTA}D{drone.drone_id}-"
                    f"{drone.current_zone.name}{RESET}"
                )
            else:
                positions.append(
                    f"{WHITE}D{drone.drone_id}-"
                    f"{drone.current_zone.name}{RESET}"
                )

        print(f"{YELLOW}Turn {self.turn:02d}{RESET}  " + " ".join(positions))

    def print_summary(self) -> None:
        """Print the simulation summary."""

        print()
        print(f"{CYAN}{'=' * 60}{RESET}")
        print(f"{BOLD}{CYAN}✓ SIMULATION COMPLETED{RESET}")
        print(f"{YELLOW}  {self.turn} turns{RESET}")
        print(f"{CYAN}{'=' * 60}{RESET}")
