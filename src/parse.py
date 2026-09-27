import re
from pathlib import Path

class ParserError(Exception):
    """Raised when the map file contains invalid data."""


class MapParser:
    """Parse a Fly-in map file."""

    def parse_hub(self):
        
        pattern = r"^hub:\s+(\S+)\s+(-?\d+)\s+(-?\d+)$"
        path = 'maps/easy/01_linear_path.txt'

        # file = open('maps/easy/01_linear_path.txt ')
        # lines = file.readline()


        with path.open() as file:
            lines = file.readline()

        # with open('01_linear_path.txt') as f:
        #     l = [line.rstrip() for line in f]

        # print(l)
        # match = re.match(pattern, line)

        # if not match:
        #     raise ParserError("Invalid hub format")

        # name = match.group(1)
        # x = int(match.group(2))
        # y = int(match.group(3))

        print(lines)

mp = MapParser()
mp.parse_hub()