import re
from pathlib import Path
from .model import Metadata, Connection, ZoneType, Drone, Graph, Zone

class ParserError(Exception):
    """Raised when the map file contains invalid data."""

class MapParser:
    """Parse a Fly-in map file."""
    def __init__(self) -> None:
        self.graph = Graph()
        self.nb_drones = 0
        self.first_line = False
        self.start_zone: Zone | None = None
        self.end_zone: Zone | None = None

    def parse_line(self, line: str) -> None:
        """Parse a single line from the map."""
        line = line.strip()
        if not line or line.startswith("#"):
            return

        if not self.first_line:
            if line.startswith("nb_drones:"):          
                self.nb_drones = self.parse_nb_drones(line)
                self.first_line = True
                return
            else:
                raise ParserError("nb_drones is not mentioned in map")
        else:
            if line.startswith("nb_drones:"):
                raise ParserError("Duplicate nb_drones")
        if (
            line.startswith("start_hub:")
            or line.startswith("hub:")
            or line.startswith("end_hub:")
        ):
            zone = self.parse_hub(line)
            if zone.name in self.graph.zones:
                raise ParserError(f"Duplicate zone name: {zone.name}")
            if line.startswith("start_hub:"):
                if self.start_zone is not None:
                    raise ParserError("Duplicate zone name start_hub")
                self.start_zone = zone
            elif line.startswith("end_hub:"):
                if self.end_zone is not None:
                    raise ParserError("Duplicate zone name end_hub")          
                self.end_zone = zone
            self.graph.add_zone(zone)
            return
        if line.startswith("connection:"):
            connection = self.parse_connection(line)
            self.graph.add_connection(connection)
            return
        raise ParserError(f"Invalid line: {line}")

    def parse_hub(self, line: str) -> Zone:
        """Parse a hub line into a Zone."""
        pattern = (
                r"^(?:start_hub|end_hub|hub):\s+"
                r"(\S+)\s+(-?\d+)\s+(-?\d+)"
                r"(?:\s+\[(.*?)\])?$"
            )
        match = re.match(pattern, line)

        if not match:
            raise ParserError(f"Invalid hub format: {line}")

        metadata = self.parse_metadata(line)

        zone_name = match.group(1)

        if "-" in zone_name:
            raise ParserError(
                f"Zone name {zone_name} cannot contain '-'."
            )
        return Zone(
            name=zone_name,
            x=int(match.group(2)),
            y=int(match.group(3)),
            zone_type=metadata.zone,
            color=metadata.color,
            max_drones=metadata.max_drones,
        )

    def valid_zone(self, value: str) -> bool:
        """Check whether a zone type is valid."""
        return value in [zone.value for zone in ZoneType]

    def parse_metadata(self, line: str) -> Metadata:
        """Parse metadata from a map line."""
        match = re.search(r"\[(.*?)\]", line)
        if not match:
            return Metadata()

        metadata = Metadata()
        seen_keys: set[str] = set()
        for item in match.group(1).split():
            try:
                key, value = item.split("=", 1)
                if key in seen_keys:
                    raise ParserError(f"Duplicate metadata key: {key}")

                seen_keys.add(key)

                if key in ("max_drones", "max_link_capacity"):
                    try:
                        number = int(value)
                    except ValueError as exc:
                        raise ParserError(
                        f"{key} must be a positive number"
                    ) from exc

                    if number <= 0:
                        raise ParserError(
                    f"{key} must be positive"
                )

                    if key == "max_drones":
                        metadata.max_drones = number
                    else:
                        metadata.max_link_capacity = number
                elif key == "color":
                    metadata.color = value
                elif key == "zone":
                    if not self.valid_zone(value):
                        raise ParserError("Invalid zone type")
                    metadata.zone = ZoneType(value)
                else:
                    raise ParserError("Invalid metadata")
            except ValueError as exc:
                raise ParserError("Invalid metadata") from exc
        return metadata


    def parse_nb_drones(self, line: str) -> int:
        """Parse the number of drones."""
        value = line.split(":", 1)[1].strip()

        try:
            nb_drones = int(value)
        except ValueError as exc:
            raise ParserError(
                "Number of drones must be an integer"
            ) from exc

        if nb_drones <= 0:
            raise ParserError("Number of drones must be positive")

        return nb_drones 

    def parse_connection(self, line: str) -> Connection:
        """Parse a connection line.""" 
        pattern = (
            r"^connection:\s+([^\s-]+)-([^\s-]+)"
            r"(?:\s+\[(.*?)\])?$"
        )
        match = re.match(pattern, line)

        if not match:
                    raise ParserError(f"Invalid connection format: {line}")
        
        metadata = self.parse_metadata(line)

        zone_a = self.graph.get_zone(match.group(1))
        zone_b = self.graph.get_zone(match.group(2))

        if zone_a is None:
            raise ParserError(f"Unknown zone {match.group(1)}")
        if zone_b is None:
            raise ParserError(f"Unknown zone {match.group(2)}")
        if self.graph.has_connection(zone_a, zone_b):
            raise ParserError(f"Duplicate connection {zone_a.name} - {zone_b.name}")

        return Connection(
            zone_a=zone_a,
            zone_b=zone_b,
            max_link_capacity=metadata.max_link_capacity,
        )

    def parse_file(self, path: Path) -> None:
        """Read and parse a map file."""
        try:
            with path.open("r", encoding="utf-8") as file:
                for line in file:
                    self.parse_line(line)
                if not self.first_line:
                    raise ParserError("Map is missing nb_drones")
                if self.start_zone is None:
                    raise ParserError("Map is missing start_hub")
                if self.end_zone is None:
                    raise ParserError("Map is missing end_hub")
        except OSError as exc:
            raise ParserError(
                f"Could not read map file: {path}"
            ) from exc