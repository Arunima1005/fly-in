import sys
from pathlib import Path

from .model import Drone
from .simulation import Simulation
from .map_selector import MapSelector
from .parse import MapParser, ParserError


def run_program(verbose: bool) -> None:
    """Select a map, parse it and run the simulation."""
    maps_directory = Path(__file__).resolve().parent.parent / "maps"

    selector = MapSelector(maps_directory)
    difficulty = selector.select_difficulty()
    map_path = selector.select_map(difficulty)

    mp = MapParser()
    mp.parse_file(map_path)

    start_zone = mp.start_zone
    end_zone = mp.end_zone
    if start_zone is None or end_zone is None:
        raise ParserError("Map is missing start_hub or end_hub")

    drones: list[Drone] = []
    for drone_id in range(1, mp.nb_drones + 1):
        drones.append(
            Drone(drone_id=drone_id, current_zone=start_zone, path_index=0)
        )

    simulation = Simulation(mp.graph, drones, end_zone, start_zone, verbose)
    simulation.run()


def main() -> None:
    """Run the program and report errors without crashing."""
    verbose = "--verbose" in sys.argv[1:]
    try:
        run_program(verbose)
    except (ParserError, ValueError, FileNotFoundError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
