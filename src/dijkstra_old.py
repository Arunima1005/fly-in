from src.model import Graph, Zone, ZoneType
from dataclasses import dataclass
import heapq


@dataclass
class DijkstraEntry:
    zone: Zone
    cost: float
    previous: Zone | None = None
    priority_count: int = 0


class Dijkstra:
    """Find the minimum-cost path between zones."""

    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def find_path(self, start: Zone, end: Zone) -> list[Zone] | None:
        """Return the minimum-cost path, preferring priority zones on ties."""
        if start.name not in self.graph.zones:
            return None

        if end.name not in self.graph.zones:
            return None

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
        if start.zone_type == ZoneType.PRIORITY:
            entries[start.name].priority_count = 1
        # (movement cost, negative priority count, zone name)
        queue: list[tuple[float, int, str]] = [
        (0, -entries[start.name].priority_count, start.name)
        ]
        visited: set[str] = set()

        while queue:
            current_cost, negative_priority, current_name = (
            heapq.heappop(queue)
            )

            if current_name in visited:
                continue

            current_entry = entries[current_name]
            current_priority = -negative_priority
            
            # Ignore outdated queue entries.
            if (
                current_cost != current_entry.cost
                or current_priority != current_entry.priority_count
            ):
                continue

            visited.add(current_name)

            if current_name == end.name:
                break
            
            neighbours = self.graph.get_neighbors(current_entry.zone)
            for neighbor in neighbours:
                if neighbor.name in visited:
                    continue

                if neighbor.zone_type == ZoneType.BLOCKED:
                    continue

                movement_cost = (
                    2 if neighbor.zone_type == ZoneType.RESTRICTED else 1
                )

                new_cost = current_cost + movement_cost
                new_priority_count = (
                current_priority
                + (1 if neighbor.zone_type == ZoneType.PRIORITY else 0)
            )
                neighbor_entry = entries[neighbor.name]

                 # First minimize movement cost, then maximize priority zones.
                if (
                    new_cost < neighbor_entry.cost
                    or (
                        new_cost == neighbor_entry.cost
                        and new_priority_count > neighbor_entry.priority_count
                    )
                ):
                    neighbor_entry.cost = new_cost
                    neighbor_entry.priority_count = new_priority_count
                    neighbor_entry.previous = current_entry.zone

                    heapq.heappush(
                        queue,
                        (new_cost, -new_priority_count, neighbor.name),
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

