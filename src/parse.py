import re
from pathlib import Path
from model import Connection, ZoneType, Drone, Graph, Zone

class ParserError(Exception):
    """Raised when the map file contains invalid data."""


class MapParser:
    """Parse a Fly-in map file."""
    def __init__(self) -> None:
        self.graph = Graph()

    def parse_line(self, line: str, line_number: int) -> None:
        """Parse a single line from the map."""
        line = line.strip()

        # print(f"Line {line_number}: {line}")

        if not line or line.startswith("#"):
            return

        if line.startswith("nb_drones:"):
            nb_drones = self.parse_nb_drones(line)
            print(f"===== nb_drones = {nb_drones}")
            return
        if (
            line.startswith("start_hub:")
            or line.startswith("hub:")
            or line.startswith("end_hub:")
        ):
            zone = self.parse_hub(line)
            self.graph.add_zone(zone)
            return
        if line.startswith("connection:"):
            connection = self.parse_connection(line)
            self.graph.add_connection(connection)
            return

        # print(f"Line {line_number}: {line}")  

    def parse_hub(self, line: str) -> Zone:
        """Parse a hub line into a Zone."""
        pattern = r"^(?:start_hub|end_hub|hub):\s+(\S+)\s+(-?\d+)\s+(-?\d+)"

        match = re.match(pattern, line)

        if not match:
            raise ParserError(f"Invalid hub format: {line}")

        metadata = self.parse_metadata(line)

        return Zone(
            name=match.group(1),
            x=int(match.group(2)),
            y=int(match.group(3)),
            zone_type=ZoneType(metadata.get("zone", "normal")),
            color=metadata.get("color"),
            max_drones=metadata.get("max_drones", 1),
            # max_link_capacity=metadata.get("max_link_capacity", 1)
        )

    def parse_metadata(self, line: str) -> dict[str, str | int]:
        """Parse metadata from a map line."""
        match = re.search(r"\[(.*?)\]", line)

        if not match:
            return {}

        metadata: dict[str, str | int] = {}

        for item in match.group(1).split():
            key, value = item.split("=", 1)

            if key in ("max_drones", "max_link_capacity"):
                metadata[key] = int(value)
            else:
                metadata[key] = value

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
        pattern = r"^connection:\s+(\S+)-(\S+)"
        match = re.search(pattern, line)

        if not match:
                    raise ParserError(f"Invalid connection format: {line}")
        
        metadata = self.parse_metadata(line)

        zone_a = self.graph.get_zone(match.group(1))
        zone_b = self.graph.get_zone(match.group(2))

        if zone_a is None or zone_b is None:
            raise ParserError("Invalid zone")

        # print(f" {match.group(1)} - {match.group(2)} [ {metadata.get("max_link_capacity", 1)}]")

        return Connection(
            zone_a=zone_a,
            zone_b=zone_b,
            max_link_capacity=metadata.get("max_link_capacity", 1),
        )

    def parse_file(self, path: Path) -> None:
        """Read and parse a map file."""
        try:
            with path.open("r", encoding="utf-8") as file:
                for line_number, line in enumerate(file, start=1):
                    self.parse_line(line, line_number)

            print("\n===== GRAPH =====")
            print(f"Zones: {len(self.graph.zones)}")
            print(f"Connections: {len(self.graph.connections)}")
        except OSError as exc:
            raise ParserError(
                f"Could not read map file: {path}"
            ) from exc