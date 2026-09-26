from enum import Enum
from pydantic import BaseModel, Field

class ZoneType(Enum):
    NORMAL = "normal"
    PRIORITY = "priority"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"

class Zone(BaseModel):
    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = 1


class Connection(BaseModel):
    """Represent a bidirectional connection between two zones."""
    zone_src: Zone
    zone_dest: Zone
    max_link_capacity: int = 1


class Drone(BaseModel):
    """Represent a drone in the simulation."""
    id: int
    current_zone: Zone
    path: list[Zone] =  Field(default_factory=list)
    path_index: int

class Graph(BaseModel):
    """Represent the Fly-in map."""

    zones: dict[str, Zone] = Field(default_factory=dict)
    connections: list[Connection] = Field(default_factory=list)

    def add_zone(self, zone: Zone) -> None:
        """Add a zone to the graph."""
        self.zones[zone.name] = zone

    def get_zone(self, name: str) -> Zone | None:
        """Return a zone by name."""
        return self.zones.get(name)

    def add_connection(self, connection: Connection) -> None:
        """Add a connection to the graph."""
        self.connections.append(connection)

    def get_neighbors(self, zone: Zone) -> list[Zone]:
        """Return zones directly connected to the given zone."""
        neighbors = []

        for connection in self.connections:
            if connection.zone_src == zone:
                neighbors.append(connection.zone_dest)
            elif connection.zone_dest == zone:
                neighbors.append(connection.zone_src)

        return neighbors

a = Zone(name="A", x=0, y=0)
b = Zone(name="B", x=1, y=0)
c = Zone(name="C", x=2, y=0)

graph = Graph()

graph.add_zone(a)
graph.add_zone(b)
graph.add_zone(c)

graph.add_connection(Connection(zone_src=a, zone_dest=b))
graph.add_connection(Connection(zone_src=b, zone_dest=c))
print(graph.get_neighbors(a))
print(graph.get_neighbors(b))