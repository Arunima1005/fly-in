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

    zone_a: Zone
    zone_b: Zone
    max_link_capacity: int = 1


class Drone(BaseModel):
    """Represent a drone in the simulation."""

    dorne_id: int
    current_zone: Zone
    path: list[Zone] = Field(default_factory=list)
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

    def has_connection(self, zone_a: Zone, zone_b: Zone) -> bool:
        """Check whether a connection already exists."""

        for connection in self.connections:
            if (connection.zone_a == zone_a and connection.zone_b == zone_b) or (
                connection.zone_b == zone_a and connection.zone_a == zone_b
            ):
                return True
        return False

    def get_neighbors(self, zone: Zone) -> list[Zone]:
        """Return zones directly connected to the given zone."""
        neighbors = []

        for connection in self.connections:
            if connection.zone_a == zone:
                neighbors.append(connection.zone_b)
            elif connection.zone_b == zone:
                neighbors.append(connection.zone_a)

        return neighbors


class Metadata(BaseModel):
    """Represent metadata for hubs and connections."""

    zone: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = 1
    max_link_capacity: int = 1
