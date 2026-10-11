from pathlib import Path

import pytest

from src.parse import MapParser, ParserError
from src.model import ZoneType


def create_parser(tmp_path: Path, content: str) -> MapParser:
    """Create a parser and parse a temporary map."""
    map_file = tmp_path / "test_map.txt"
    map_file.write_text(content, encoding="utf-8")

    parser = MapParser()
    parser.parse_file(map_file)

    return parser


def test_parse_nb_drones(tmp_path: Path) -> None:
    """Test parsing the number of drones."""
    content = """\
nb_drones: 5
start_hub: start 0 0
end_hub: goal 2 0
"""

    parser = create_parser(tmp_path, content)

    # This will eventually be replaced by parser.nb_drones
    # once we store nb_drones in the parser.
    assert parser.nb_drones == 5


def test_parse_nb_drones_first_line(tmp_path: Path) -> None:
    """Test parsing the number of drones."""
    content = """\
    start_hub: start 0 0
    nb_drones: 5
    end_hub: goal 2 0
    """
    with pytest.raises(ParserError, match="nb_drones is not mentioned in map"):
        create_parser(tmp_path, content)

def test_parse_zones(tmp_path: Path) -> None:
    """Test parsing zones."""
    content = """\
nb_drones: 2

start_hub: start 0 0
hub: A 1 0
end_hub: goal 2 0
"""

    parser = create_parser(tmp_path, content)

    assert len(parser.graph.zones) == 3
    assert parser.graph.get_zone("start") is not None
    assert parser.graph.get_zone("A") is not None
    assert parser.graph.get_zone("goal") is not None


def test_parse_zone_coordinates(tmp_path: Path) -> None:
    """Test parsing positive and negative coordinates."""
    content = """\
nb_drones: 2

start_hub: start -10 20
hub: A -5 -7
end_hub: goal 30 40
"""

    parser = create_parser(tmp_path, content)

    zone = parser.graph.get_zone("A")

    assert zone is not None
    assert zone.x == -5
    assert zone.y == -7

def test_duplicate_nb_drones(tmp_path: Path) -> None:
    """Test that nb_drones cannot be defined twice."""
    content = """\
nb_drones: 5
nb_drones: 10
"""

    with pytest.raises(ParserError, match="Duplicate nb_drones"):
        create_parser(tmp_path, content)

def test_invalid_zone_type(tmp_path: Path) -> None:
    """Test that an invalid zone type is rejected."""
    content = """\
nb_drones: 2
hub: A 1 0 [zone=foobar]
"""

    with pytest.raises(ParserError, match="Invalid zone type"):
        create_parser(tmp_path, content)

def test_invalid_max_drones(tmp_path: Path) -> None:
    """Test that max_drones must be positive."""
    content = """\
nb_drones: 2
hub: A 1 0 [max_drones=0]
"""

    with pytest.raises(ParserError, match="max_drones must be positive"):
        create_parser(tmp_path, content)


def test_invalid_max_drones_string(tmp_path: Path) -> None:
    """Test that max_drones must be positive."""
    content = """\
nb_drones: 2
hub: A 1 0 [max_drones=abc]
"""

    with pytest.raises(
    ParserError,
    match="max_drones must be a positive number",
):
        create_parser(tmp_path, content)

def test_invalid_metadata_format(tmp_path: Path) -> None:
    """Test that metadata must contain a key and value."""
    content = """\
nb_drones: 2
hub: A 1 0 [max_drones]
"""

    with pytest.raises(ParserError, match="Invalid metadata max_drones"):
        create_parser(tmp_path, content)

def test_comments_before_nb_drones(tmp_path: Path) -> None:
    """Test that comments and blank lines are ignored."""
    content = """\
# This is a comment

# Another comment
nb_drones: 5
start_hub: start 0 0
end_hub: goal 2 0
"""
    parser = create_parser(tmp_path, content)

    assert parser.nb_drones == 5


def test_missing_nb_drones(tmp_path: Path) -> None:
    """Test that nb_drones is required."""
    content = ""

    with pytest.raises(ParserError, match="Map is missing nb_drones"):
        create_parser(tmp_path, content)

def test_parse_zone_metadata(tmp_path: Path) -> None:
    """Test parsing zone metadata."""
    content = """\
nb_drones: 2

start_hub: start 0 0 [color=green]
hub: A 1 0 [zone=priority color=blue max_drones=3]
end_hub: goal 2 0 [color=red]
"""

    parser = create_parser(tmp_path, content)

    zone = parser.graph.get_zone("A")

    assert zone is not None
    assert zone.zone_type == ZoneType.PRIORITY
    assert zone.color == "blue"
    assert zone.max_drones == 3


def test_parse_connections(tmp_path: Path) -> None:
    """Test parsing connections."""
    content = """\
nb_drones: 2

start_hub: start 0 0
hub: A 1 0
end_hub: goal 2 0

connection: start-A
connection: A-goal
"""

    parser = create_parser(tmp_path, content)

    assert len(parser.graph.connections) == 2


def test_connection_capacity(tmp_path: Path) -> None:
    """Test connection capacity metadata."""
    content = """\
nb_drones: 2

start_hub: start 0 0
hub: A 1 0
end_hub: goal 2 0

connection: start-A [max_link_capacity=3]
"""

    parser = create_parser(tmp_path, content)

    connection = parser.graph.connections[0]

    assert connection.max_link_capacity == 3


def test_default_connection_capacity(tmp_path: Path) -> None:
    """Test default connection capacity."""
    content = """\
nb_drones: 2

start_hub: start 0 0
hub: A 1 0
end_hub: goal 2 0

connection: start-A
"""

    parser = create_parser(tmp_path, content)

    connection = parser.graph.connections[0]

    assert connection.max_link_capacity == 1


def test_duplicate_zone(tmp_path: Path) -> None:
    """Test duplicate zone names are rejected."""
    content = """\
nb_drones: 2

start_hub: start 0 0
hub: A 1 0
hub: A 2 0
end_hub: goal 3 0
"""

    with pytest.raises(ParserError, match="Duplicate zone"):
        create_parser(tmp_path, content)


def test_unknown_zone_in_connection(tmp_path: Path) -> None:
    """Test connections cannot reference unknown zones."""
    content = """\
nb_drones: 2

start_hub: start 0 0
hub: A 1 0
end_hub: goal 2 0

connection: A-unknown
"""

    with pytest.raises(ParserError, match="Unknown zone"):
        create_parser(tmp_path, content)


def test_duplicate_connection(tmp_path: Path) -> None:
    """Test duplicate connections are rejected."""
    content = """\
nb_drones: 2

start_hub: start 0 0
hub: A 1 0
end_hub: goal 2 0

connection: start-A
connection: A-start
"""

    with pytest.raises(ParserError, match="Duplicate connection"):
        create_parser(tmp_path, content)

def test_zone_name_cannot_contain_dash(tmp_path: Path) -> None:
    """Test that zone names cannot contain dashes."""
    content = """\
nb_drones: 2
hub: my-zone 1 0
"""

    with pytest.raises(
        ParserError,
        match="Zone name my-zone cannot contain",
    ):
        create_parser(tmp_path, content)

def test_invalid_x_coordinate(tmp_path: Path) -> None:
    """Test that x coordinate must be an integer."""
    content = """\
nb_drones: 2
hub: A abc 20
"""

    with pytest.raises(ParserError, match="Invalid hub format"):
        create_parser(tmp_path, content)

def test_invalid_y_coordinate(tmp_path: Path) -> None:
    """Test that y coordinate must be an integer."""
    content = """\
nb_drones: 2
hub: A 10 abc
"""

    with pytest.raises(ParserError, match="Invalid hub format"):
        create_parser(tmp_path, content)

def test_decimal_coordinate(tmp_path: Path) -> None:
    """Test that coordinates cannot be decimal values."""
    content = """\
nb_drones: 2
hub: A 10.5 20
"""

    with pytest.raises(ParserError, match="Invalid hub format"):
        create_parser(tmp_path, content)

def test_invalid_text_after_coordinates(tmp_path: Path) -> None:
    """Test that unexpected text after coordinates is rejected."""
    content = """\
nb_drones: 2
hub: A 10 20 garbage
"""

    with pytest.raises(ParserError, match="Invalid hub format"):
        create_parser(tmp_path, content)

def test_parse_start_and_end_hub(tmp_path: Path) -> None:
    """Test that start and end hubs are identified."""
    content = """\
nb_drones: 2
start_hub: start 0 0
hub: A 1 0
end_hub: goal 2 0
"""

    parser = create_parser(tmp_path, content)

    assert parser.start_zone is not None
    assert parser.start_zone.name == "start"
    assert parser.end_zone is not None
    assert parser.end_zone.name == "goal"

def test_parse_duplicate_start_hub(tmp_path: Path) -> None:
    """Test that duplicate start hubs are rejected."""
    content = """\
        nb_drones: 2
start_hub: A 0 0
start_hub: B 1 1
end_hub: C 2 2
"""
    with pytest.raises(ParserError, match="Duplicate zone name start_hub"):
        create_parser(tmp_path, content)


def test_parse_duplicate_end_hub(tmp_path: Path) -> None:
    """Test that duplicate end hubs are rejected."""
    content = """\
        nb_drones: 2
start_hub: A 0 0
end_hub: B 1 1
end_hub: C 2 2
"""
    with pytest.raises(ParserError, match="Duplicate zone name end_hub"):
        create_parser(tmp_path, content)

def test_parse_missing_start_hub(tmp_path: Path) -> None:
    """Test that a missing start hub is rejected."""
    content = """\
            nb_drones: 2
    hub: B 1 1
    end_hub: C 2 2
    """
    with pytest.raises(ParserError, match="Map is missing start_hub"):
            create_parser(tmp_path, content)
def test_parse_missing_end_hub(tmp_path: Path) -> None:
    """Test that a missing end hub is rejected."""
    content = """\
            nb_drones: 2
    start_hub: B 1 1
    hub: C 2 2
    """
    with pytest.raises(ParserError, match="Map is missing end_hub"):
            create_parser(tmp_path, content)


def test_invalid_text_after_connection(tmp_path: Path) -> None:
    """Test that unexpected text after a connection is rejected."""
    content = """\
nb_drones: 2
start_hub: start 0 0
hub: A 1 0
end_hub: goal 2 0
connection: start-A garbage
"""

    with pytest.raises(ParserError, match="Invalid connection format"):
        create_parser(tmp_path, content)

def test_invalid_connection_missing_second_zone(tmp_path: Path) -> None:
    """Test that a connection must contain two zones."""
    content = """\
nb_drones: 2
start_hub: start 0 0
hub: A 1 0
end_hub: goal 2 0
connection: start-
"""

    with pytest.raises(ParserError, match="Invalid connection format"):
        create_parser(tmp_path, content)

def test_invalid_connection_missing_first_zone(tmp_path: Path) -> None:
    """Test that a connection must contain two zones."""
    content = """\
nb_drones: 2
start_hub: start 0 0
hub: A 1 0
end_hub: goal 2 0
connection: -A
"""

    with pytest.raises(ParserError, match="Invalid connection format"):
        create_parser(tmp_path, content)

def test_invalid_connection_too_many_separators(tmp_path: Path) -> None:
    """Test that a connection contains exactly two zone names."""
    content = """\
nb_drones: 2
start_hub: start 0 0
hub: A 1 0
end_hub: goal 2 0
connection: start-A-goal
"""

    with pytest.raises(ParserError, match="Invalid connection format"):
        create_parser(tmp_path, content)

def test_invalid_max_link_capacity(tmp_path: Path) -> None:
    """Test that max_link_capacity must be positive."""
    content = """\
nb_drones: 2
start_hub: start 0 0
hub: A 1 0
end_hub: goal 2 0
connection: start-A [max_link_capacity=0]
"""

    with pytest.raises(
        ParserError,
        match="max_link_capacity must be positive",
    ):
        create_parser(tmp_path, content)

def test_negative_max_link_capacity(tmp_path: Path) -> None:
    """Test that max_link_capacity cannot be negative."""
    content = """\
nb_drones: 2
start_hub: start 0 0
hub: A 1 0
end_hub: goal 2 0
connection: start-A [max_link_capacity=-1]
"""

    with pytest.raises(
        ParserError,
        match="max_link_capacity must be positive",
    ):
        create_parser(tmp_path, content)

def test_invalid_line(tmp_path: Path) -> None:
    """Test that an unknown map line is rejected."""
    content = """\
nb_drones: 2
start_hub: start 0 0
end_hub: goal 2 0
something_invalid
"""

    with pytest.raises(ParserError, match="Invalid line"):
        create_parser(tmp_path, content)

def test_duplicate_zone_metadata(tmp_path: Path) -> None:
    content = """\
nb_drones: 2
start_hub: start 0 0
hub: A 1 0 [zone=normal zone=priority]
end_hub: goal 2 0
"""
    with pytest.raises(ParserError, match="Duplicate metadata key: zone"):
        create_parser(tmp_path, content)

@pytest.mark.parametrize(
    "metadata",
    [
        "zone=normal zone=priority",
        "color=green color=red",
        "max_drones=2 max_drones=5",
        "max_link_capacity=2 max_link_capacity=4",
    ],
)
def test_duplicate_metadata(
    tmp_path: Path,
    metadata: str,
) -> None:
    content = f"""\
nb_drones: 2
start_hub: start 0 0
hub: A 1 0 [{metadata}]
end_hub: goal 2 0
"""
    with pytest.raises(ParserError, match="Duplicate metadata key"):
        create_parser(tmp_path, content)

@pytest.mark.parametrize(
    "metadata",
    [
        "max_link_capacity=0",
        "max_link_capacity=-3",
        "max_link_capacity=abc",
    ],
)
def test_invalid_max_link_capacity(
    tmp_path: Path,
    metadata: str,
) -> None:
    content = f"""\
nb_drones: 2
start_hub: start 0 0
hub: A 1 0
end_hub: goal 2 0
connection: start-A [{metadata}]
"""
    with pytest.raises(ParserError):
        create_parser(tmp_path, content)

@pytest.mark.parametrize(
    "metadata",
    [
        "max_drones=0",
        "max_drones=-2",
        "max_drones=abc",
    ],
)
def test_invalid_max_drones(
    tmp_path: Path,
    metadata: str,
) -> None:
    content = f"""\
nb_drones: 2
start_hub: start 0 0
hub: A 1 0 [{metadata}]
end_hub: goal 2 0
"""
    with pytest.raises(ParserError):
        create_parser(tmp_path, content)
def test_parse_max_link_capacity(tmp_path: Path) -> None:
    content = """\
nb_drones: 3
start_hub: start 0 0
hub: A 1 0
end_hub: goal 2 0
connection: start-A [max_link_capacity=4]
"""
    parser = create_parser(tmp_path, content)

    connection = parser.graph.connections[0]
    assert connection.max_link_capacity == 4

def test_parse_max_drones(tmp_path: Path) -> None:
    content = """\
nb_drones: 3
start_hub: start 0 0
hub: A 1 0 [max_drones=5]
end_hub: goal 2 0
"""
    parser = create_parser(tmp_path, content)

    zone = parser.graph.get_zone("A")
    assert zone is not None
    assert zone.max_drones == 5