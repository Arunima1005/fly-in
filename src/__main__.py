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


def load_simulation(map_path: Path, verbose: bool) -> Simulation:
    """Parse a map file and create a fresh simulation for it."""
    mp = MapParser()
    mp.parse_file(map_path)

    start_zone = mp.start_zone
    end_zone = mp.end_zone
    if start_zone is None or end_zone is None:
        raise ParserError("Map is missing start_hub or end_hub")

    drones = [
        Drone(drone_id=drone_id, current_zone=start_zone, path_index=0)
        for drone_id in range(1, mp.nb_drones + 1)
    ]
    return Simulation(mp.graph, drones, end_zone, start_zone, verbose)


def run_terminal(verbose: bool, map_file: Path | None) -> None:
    """Pick a map in the terminal (unless given) and print the turns."""
    if map_file is None:
        selector = MapSelector(MapSelector.DEFAULT_DIRECTORY)
        difficulty = selector.select_difficulty()
        map_file = selector.select_map(difficulty)
    load_simulation(map_file, verbose).run()


def run_visual_app(verbose: bool, map_file: Path | None) -> None:
    """Switch between the map menu and the visualizer until the user quits."""
    # Imported here so the terminal mode works without pygame/a display.
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame
    from .map_selection_ui import MapSelectionUI
    from .visualizer import Visualizer

    try:
        pygame.display.init()
        pygame.font.init()
        info = pygame.display.Info()
        size = (int(info.current_w * 0.85), int(info.current_h * 0.85))
        screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        pygame.display.set_caption("Fly-in")

        menu = MapSelectionUI(screen)
        map_path = map_file          # with --file, start directly in the map

        while True:
            if map_path is None:
                map_path = menu.select_map(MapSelector.DEFAULT_DIRECTORY)
                if map_path is None:     # window closed / Esc in the menu
                    return

            simulation = load_simulation(map_path, verbose)
            simulation.assign_paths()
            if verbose:
                simulation.print_header()

            back_to_menu = Visualizer(simulation, screen).run_visual()

            if verbose and simulation.all_drones_finished():
                simulation.print_summary()
            if not back_to_menu:         # Esc / window closed: quit
                return
            map_path = None              # M pressed: show the menu again
    except pygame.error as error:
        raise VisualError(f"Cannot open the visualizer: {error}") from error
    finally:
        pygame.quit()                    # only once, when the program ends


def run_program(verbose: bool, visual: bool, map_file: Path | None) -> None:
    """Run the terminal mode or the pygame app."""
    if visual:
        run_visual_app(verbose, map_file)
    else:
        run_terminal(verbose, map_file)


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
