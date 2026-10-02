from src.model import Graph, Zone, ZoneType
from dataclasses import dataclass
import heapq


@dataclass
class DijkstraEntry:
    zone: Zone
    cost: float
    previous: Zone | None = None


class Dijkstra:
    """Find the minimum-cost path between zones."""

    def __init__(self, graph: Graph) -> None:
        self.graph = graph

    def find_path(self, start: Zone, end: Zone) -> list[Zone] | None:
        """Return the minimum-cost path."""
        if start.name not in self.graph.zones:
            return None

        if end.name not in self.graph.zones:
            return None

        entries: dict[str, DijkstraEntry] = {}
        
        for zone in self.graph.zones.values():
            entries[zone.name] = DijkstraEntry(
                zone=zone,
                cost=float("inf"),
            )

        entries[start.name].cost = 0
        queue: list[tuple[float, str]] = [(0, start.name)]
        visited: set[str] = set()

        while queue:
            current_cost, current_name = heapq.heappop(queue)

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

                movement_cost = (
                    2 if neighbor.zone_type == ZoneType.RESTRICTED else 1
                )

                new_cost = current_cost + movement_cost
                neighbor_entry = entries[neighbor.name]

                if new_cost < neighbor_entry.cost:
                    neighbor_entry.cost = new_cost
                    neighbor_entry.previous = current_entry.zone
                    heapq.heappush(queue, (new_cost, neighbor.name))

        if end.name not in visited:
            return None

        path: list[Zone] = []
        current: Zone | None = end

        while current is not None:
            path.append(current)
            current = entries[current.name].previous

        path.reverse()
        return path

