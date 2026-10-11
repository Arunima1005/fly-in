from dataclasses import dataclass
import heapq
from collections import Counter

from .model import Graph, Zone, ZoneType  # use your actual module here


@dataclass
class DijkstraEntry:
    """Best known cost and route to one zone during a path search."""
    zone: Zone
    cost: float
    priority_count: int = 0
    previous: Zone | None = None


class Dijkstra:
    """Find the minimum-cost path between zones, preferring paths that
    pass through more priority zones whenever two paths tie on cost."""
    CONGESTION_WEIGHT = 0.01

    def __init__(self, graph: Graph) -> None:
        """Store the graph to search in."""
        self.graph = graph

    def find_path(
    self,
    start: Zone,
    end: Zone,
    zone_usage: "Counter[str] | None" = None,
) -> list[Zone] | None:
        """Return the minimum-cost path, breaking cost ties first in
        favor of the path with more priority zones, then in favor of
        the path whose zones have been used by fewer earlier drones.

        `zone_usage` is a running count of how many already-planned
        drones pass through each zone. Pass the same Counter in for
        every drone in a fleet (updating it after each drone is
        planned) and later drones will naturally prefer an alternate,
        equally-cheap route over a route earlier drones already took.
        Leave it out for a plain single-drone lookup.
        """
        if zone_usage is None:
            zone_usage = Counter()

        if start.name not in self.graph.zones:
            return None

        if end.name not in self.graph.zones:
            return None

        # Always work with the graph's own copies, in case the caller
        # passed a different Zone object that happens to share a name.
        start = self.graph.zones[start.name]
        end = self.graph.zones[end.name]

        if start.zone_type == ZoneType.BLOCKED:
            return None

        if end.zone_type == ZoneType.BLOCKED:
            return None

        entries: dict[str, DijkstraEntry] = {}
        for zone in self.graph.zones.values():
            entries[zone.name] = DijkstraEntry(
                zone=zone,
                cost=float("inf"),
            )

        entries[start.name].cost = 0

        # Heap items: (cost, -priority_count, zone_name). heapq always
        # pops the smallest tuple, so cost decides first; only when two
        # entries share the same cost does the second slot get compared,
        # and the more negative value (= the higher priority_count) wins.
        queue: list[tuple[float, int, str]] = [(0, 0, start.name)]
        visited: set[str] = set()

        while queue:
            current_cost, _neg_priority, current_name = heapq.heappop(queue)

            if current_name in visited:
                continue
            current_entry = entries[current_name]
            visited.add(current_name)

            if current_name == end.name:
                break

            neighbours = self.graph.get_neighbors(current_entry.zone)
            for neighbor in neighbours:
                if neighbor.name in visited:
                    continue

                if neighbor.zone_type == ZoneType.BLOCKED:
                    continue

                base_cost = 2 if neighbor.zone_type == ZoneType.RESTRICTED else 1
                congestion = self.CONGESTION_WEIGHT * zone_usage[neighbor.name]
                movement_cost = base_cost + congestion
                is_priority = neighbor.zone_type == ZoneType.PRIORITY

                new_cost = current_cost + movement_cost
                new_priority = current_entry.priority_count + (1 if is_priority else 0)
                neighbor_entry = entries[neighbor.name]

                candidate_key = (new_cost, -new_priority)
                current_key = (
                    neighbor_entry.cost,
                    -neighbor_entry.priority_count,
                )

                if candidate_key < current_key:
                    neighbor_entry.cost = new_cost
                    neighbor_entry.priority_count = new_priority
                    neighbor_entry.previous = current_entry.zone

                    heapq.heappush(
                        queue,
                        (new_cost, -new_priority, neighbor.name),
                    )

        if end.name not in visited:
            return None

        path: list[Zone] = []
        current: Zone | None = end

        while current is not None:
            path.append(current)
            current = entries[current.name].previous

        path.reverse()
        return path