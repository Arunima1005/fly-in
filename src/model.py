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
