import argparse
import os
import sys
from pathlib import Path

from .map_selector import MapSelector
from .model import Drone
from .parse import MapParser, ParserError
from .simulation import Simulation


class VisualError(Exception):
    """Raised when the pygame window cannot be used."""


class FlyIn:
    """Command line entry point: reads the options and runs the right mode."""

    def __init__(
        self,
        verbose: bool = False,
        visual: bool = False,
        map_path: Path | None = None,
    ) -> None:
        """Store the options for this run.

        map_path is the --file option. When it is None, the map is chosen
        from a menu instead.
        """
        self.verbose = verbose
        self.visual = visual
        self.map_path = map_path

    @classmethod
    def from_command_line(cls) -> "FlyIn":
        """Create a FlyIn from the command line options."""
        parser = argparse.ArgumentParser(description="Fly-in drone simulation")
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
        return cls(args.verbose, args.visual, args.file)

    def run(self) -> None:
        """Run the chosen mode and report errors without crashing."""
        try:
            if self.visual:
                self.run_visual_app()
            else:
                self.run_terminal()
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

    def load_simulation(self, map_path: Path) -> Simulation:
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
        return Simulation(
            mp.graph, drones, end_zone, start_zone, self.verbose
        )

    def run_terminal(self) -> None:
        """Pick a map in the terminal (unless given) and print the turns."""
        map_path = self.map_path
        if map_path is None:
            selector = MapSelector(MapSelector.DEFAULT_DIRECTORY)
            difficulty = selector.select_difficulty()
            map_path = selector.select_map(difficulty)
        self.load_simulation(map_path).run()

    def run_visual_app(self) -> None:
        """Switch between the map menu and the visualizer until quitting."""
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
            # With --file, start directly in that map.
            map_path = self.map_path

            while True:
                if map_path is None:
                    map_path = menu.select_map(MapSelector.DEFAULT_DIRECTORY)
                    if map_path is None:  # window closed / Esc in the menu
                        return

                simulation = self.load_simulation(map_path)
                simulation.assign_paths()
                if self.verbose:
                    simulation.print_header()

                back_to_menu = Visualizer(simulation, screen).run_visual()

                if self.verbose and simulation.all_drones_finished():
                    simulation.print_summary()
                if not back_to_menu:  # Esc / window closed: quit
                    return
                map_path = None  # M pressed: show the menu again
        except pygame.error as error:
            raise VisualError(
                f"Cannot open the visualizer: {error}"
            ) from error
        finally:
            pygame.quit()  # only once, when the program ends


if __name__ == "__main__":
    FlyIn.from_command_line().run()
