import os
import sys
from pathlib import Path

from .model import Drone
from .simulation import Simulation
from .map_selector import MapSelector
from .parse import MapParser, ParserError

USAGE = "Usage: python -m src [--verbose] [--visual]"
VALID_FLAGS = {"--verbose", "--visual"}


def run_program(verbose: bool, visual: bool) -> None:
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

    if not visual:
        simulation.run()
        return

    # Imported here so the terminal mode works without pygame/a display.
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    from .visualizer import run_visual

    simulation.assign_paths()
    if verbose:
        simulation.print_header()
    run_visual(simulation, mp.graph, start_zone, end_zone)
    if verbose and simulation.all_drones_finished():
        simulation.print_summary()


def main() -> None:
    """Run the program and report errors without crashing."""
    flags = sys.argv[1:]
    unknown = [flag for flag in flags if flag not in VALID_FLAGS]
    if unknown:
        print(f"Error: unknown option {unknown[0]}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        sys.exit(1)

    try:
        run_program("--verbose" in flags, "--visual" in flags)
    except (ParserError, ValueError, FileNotFoundError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
