from .dijkstra import Dijkstra
from .model import Drone, Zone, Graph, ZoneType

import sys
from collections import Counter


class Color:
    """ANSI escape codes for colored terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    WHITE = "\033[97m"
    MAGENTA = "\033[95m"

    # Zone colors from the map file, as 256-color terminal codes.
    ZONE_CODES = {
        "black": 244,  # gray, so it stays visible on a dark terminal
        "blue": 33,
        "brown": 130,
        "crimson": 161,
        "cyan": 51,
        "darkred": 88,
        "gold": 220,
        "gray": 245,
        "green": 40,
        "grey": 245,
        "lime": 118,
        "magenta": 201,
        "maroon": 52,
        "orange": 208,
        "pink": 211,
        "purple": 129,
        "red": 196,
        "violet": 177,
        "white": 255,
        "yellow": 226,
    }

    @classmethod
    def zone(cls, zone: Zone) -> str:
        """Return the code for a zone's map color, or white if unknown."""
        code = cls.ZONE_CODES.get(zone.color or "")
        if code is None:
            return cls.WHITE
        return f"\033[38;5;{code}m"


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
                    f"{Color.RED}Simulation stopped: no drones can move."
                    f"{Color.RESET}",
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
        print(f"{Color.CYAN}{'=' * 60}{Color.RESET}")
        print(f"{Color.BOLD}{Color.CYAN}"
              f"              FLY-IN - DRONE SIMULATION{Color.RESET}")
        print(f"{Color.CYAN}{'=' * 60}{Color.RESET}")
        print()

        print(f"{Color.BOLD}{Color.CYAN}SIMULATION INFO{Color.RESET}")
        print(f"{Color.GREEN}✓ Drones : {len(self.drones)}{Color.RESET}")
        print(f"{Color.GREEN}✓ Start  : {self.start_zone.name}{Color.RESET}")
        print(f"{Color.GREEN}✓ End    : {self.end_zone.name}{Color.RESET}")
        print()

        print(f"{Color.CYAN}{'-' * 60}{Color.RESET}")
        print(f"{Color.BOLD}{Color.CYAN}"
              f"                    SIMULATION{Color.RESET}")
        print(f"{Color.CYAN}{'-' * 60}{Color.RESET}")

    def print_status(self) -> None:
        """Print every drone's position, with zone names in map colors.

        The drone ID shows its state (magenta waiting at the start, white
        on the way, red in flight to a restricted zone, green delivered).
        The zone name uses the color given in the map file.
        """
        positions = []

        for drone in self.drones:
            zone = drone.current_zone
            if drone.movement_remaining > 0:
                state = Color.RED
                destination = drone.path[drone.path_index + 1]
                place = (
                    f"{Color.zone(zone)}{zone.name}{Color.RESET}{state}-"
                    f"{Color.zone(destination)}{destination.name}"
                )
            else:
                if zone == self.end_zone:
                    state = Color.GREEN
                elif zone == self.start_zone:
                    state = Color.MAGENTA
                else:
                    state = Color.WHITE
                place = f"{Color.zone(zone)}{zone.name}"
            positions.append(
                f"{state}D{drone.drone_id}-{place}{Color.RESET}"
            )

        print(
            f"{Color.YELLOW}Turn {self.turn:02d}{Color.RESET}  "
            + " ".join(positions)
        )

    def print_summary(self) -> None:
        """Print the simulation summary."""

        print()
        print(f"{Color.CYAN}{'=' * 60}{Color.RESET}")
        print(f"{Color.BOLD}{Color.CYAN}✓ SIMULATION COMPLETED{Color.RESET}")
        print(f"{Color.YELLOW}  {self.turn} turns{Color.RESET}")
        print(f"{Color.CYAN}{'=' * 60}{Color.RESET}")
