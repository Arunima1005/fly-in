import os
import sys
from pathlib import Path
import argparse
from .model import Drone
from .simulation import Simulation
from .map_selector import MapSelector
from .parse import MapParser, ParserError


class VisualError(Exception):
    """Raised when the pygame window cannot be used."""


def run_program(verbose: bool, visual: bool, map_file: Path | None) -> None:
    """Select a map, parse it and run the simulation."""
    if map_file is None:
        maps_directory = Path(__file__).resolve().parent.parent / "maps"
        selector = MapSelector(maps_directory)
        difficulty = selector.select_difficulty()
        map_path = selector.select_map(difficulty)
    else:
        map_path = map_file
    mp = MapParser()
    mp.parse_file(map_path)

    start_zone = mp.start_zone
    end_zone = mp.end_zone
    if start_zone is None or end_zone is None:
        raise ParserError("Map is missing start_hub or end_hub")

    drones: list[Drone] = []
    for drone_id in range(1, mp.nb_drones + 1):
        drones.append(
            Drone(
                drone_id=drone_id,
                current_zone=start_zone,
                path_index=0,
            )
        )

    simulation = Simulation(mp.graph, drones, end_zone, start_zone, verbose)

    if not visual:
        simulation.run()
        return

    # Imported here so the terminal mode works without pygame/a display.
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame
    from .visualizer import Visualizer

    simulation.assign_paths()
    if verbose:
        simulation.print_header()
    try:
        visualizer = Visualizer(simulation)
        visualizer.run_visual()
    except pygame.error as error:
        raise VisualError(f"Cannot open the visualizer: {error}") from error
    finally:
        pygame.quit()
    if verbose and simulation.all_drones_finished():
        simulation.print_summary()


def main() -> None:
    """Run the program and report errors without crashing."""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--visual",
        action="store_true",
        help="Enable visual mode",
    )

    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="Path of map",
    )
    args = parser.parse_args()

    try:
        run_program(args.verbose, args.visual, args.file)
    except (
        ParserError,
        ValueError,
        FileNotFoundError,
        VisualError,
    ) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
