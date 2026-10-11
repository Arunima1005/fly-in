from time import perf_counter
import pygame
from functools import lru_cache
from .simulation import Simulation
from .model import Drone, Graph, Zone, ZoneType
from pathlib import Path

class Visualizer:
    """Pygame visualization of the simulation (enabled with --visual)."""

    PYGAME_ZONE_COLORS = {
        "black": (30, 30, 30),
        "blue": (0, 120, 255),
        "brown": (165, 90, 40),
        "crimson": (220, 20, 60),
        "cyan": (0, 220, 220),
        "darkred": (139, 0, 0),
        "gold": (255, 200, 0),
        "gray": (128, 128, 128),
        "green": (0, 200, 80),
        "grey": (128, 128, 128),
        "lime": (120, 255, 80),
        "magenta": (255, 0, 200),
        "maroon": (128, 0, 0),
        "orange": (255, 140, 0),
        "pink": (255, 120, 180),
        "purple": (160, 80, 220),
        "red": (255, 50, 50),
        "violet": (140, 80, 220),
        "white": (240, 240, 240),
        "yellow": (255, 220, 0),
    }

    def __init__(self, simulation: Simulation) -> None:
        """Open the window and load images and fonts."""
        pygame.display.init()
        pygame.font.init()

        info = pygame.display.Info()
        size = (int(info.current_w * 0.85), int(info.current_h * 0.85))
        self.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
        pygame.display.set_caption("Fly-in")

        self.simulation = simulation
        self.graph = simulation.graph            # already stored there
        self.background = self._make_sky_background()
        self.drone_image = self._load_drone_image()
        self.font = pygame.font.SysFont(None, 24)
        self.badge_font = pygame.font.SysFont(None, 16)

        # Map layout, recalculated when the window is resized.
        self.offset_x = 0
        self.offset_y = 0
        self.scale = 1.0
        self._calculate_map_layout()


    def _load_drone_image(self) -> pygame.Surface:
        """Load and scale the drone image."""
        image = pygame.image.load(
            str(Path(__file__).resolve().parent.parent / "assets" / "drone.png")
        ).convert_alpha()

        return pygame.transform.smoothscale(image, (24, 24))



    def _calculate_map_layout(
        self,
    ) -> None:
        """Fit the map into the window and store offset and scale."""
        xs = [zone.x for zone in self.graph.zones.values()]
        ys = [zone.y for zone in self.graph.zones.values()]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        margin = 100
        available_width = self.screen.get_width() - 2 * margin
        available_height = self.screen.get_height() - 2 * margin

        map_width = max_x - min_x
        map_height = max_y - min_y

        scale_x = available_width / map_width if map_width else float("inf")
        scale_y = available_height / map_height if map_height else float("inf")
        scale = min(scale_x, scale_y)
        if scale == float("inf"):
            scale = 1


        map_center_x = (min_x + max_x) / 2
        map_center_y = (min_y + max_y) / 2

        screen_center_x = self.screen.get_width() / 2
        screen_center_y = self.screen.get_height() / 2

        self.offset_x = int(screen_center_x - map_center_x * scale)
        self.offset_y = int(screen_center_y + map_center_y * scale)
        self.scale = scale


    def _make_sky_background(self) -> pygame.Surface:
        """Create a vertical sky gradient the size of the window."""
        width, height = self.screen.get_size()
        sky = pygame.Surface((width, height))
        top = (135, 185, 230)
        bottom = (225, 238, 248)

        for y in range(height):
            t = y / height
            color = tuple(
                int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)
            )
            pygame.draw.line(sky, color, (0, y), (width, y))

        return sky


    def draw_diamond(self,
        color: tuple[int, int, int],
        position: tuple[int, int],
        size: int,
    ) -> None:
        """Draw a filled diamond centered on position."""
        x, y = position

        points = [
            (x, y - size),
            (x + size, y),
            (x, y + size),
            (x - size, y),
        ]

        pygame.draw.polygon(self.screen, color, points)

    def map_to_screen(self,
        x: float,
        y: float,
    ) -> tuple[int, int]:
        """Convert map coordinates to pixel coordinates."""
        screen_x = self.offset_x + x * self.scale
        screen_y = self.offset_y - y * self.scale

        return screen_x, screen_y


    def draw_connection(self,
        zone_a: Zone,
        zone_b: Zone,
    ) -> None:
        """Draw the line for a connection between two zones."""
        start = self.map_to_screen(
            zone_a.x,
            zone_a.y,
        )

        end = self.map_to_screen(
            zone_b.x,
            zone_b.y,
        )

        pygame.draw.line(
        self.screen,
        (60, 75, 95),
        start,
        end,
        2,
    )


    def draw_zone(self,
        zone: Zone,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        """Draw one zone with a shape that shows its type."""
        position = self.map_to_screen(
            zone.x,
            zone.y,
        )

        color = self.PYGAME_ZONE_COLORS.get(
            zone.color or "blue",
            (0, 150, 255),
        )

        size = 20
        outline = (30, 30, 30)
        if zone.zone_type == ZoneType.PRIORITY:
            x, y = position
            self.draw_diamond(color, position, size)
            pygame.draw.polygon(self.screen, outline,
                        [(x, y - size), (x + size, y), (x, y + size), (x - size, y)], 2)
        elif zone.zone_type == ZoneType.RESTRICTED:
            pygame.draw.rect(
                self.screen,
                color,
                (position[0] - size, position[1] - size, size * 2, size * 2),
            )
            pygame.draw.rect(self.screen, outline,
                        (position[0] - size, position[1] - size, size * 2, size * 2), 2)

        elif zone.zone_type == ZoneType.BLOCKED:
            points = [
                (position[0], position[1] - size),
                (position[0] + size, position[1] + size),
                (position[0] - size, position[1] + size),
            ]
            pygame.draw.polygon(self.screen, color, points)
            pygame.draw.polygon(self.screen, outline, points, 2)

        else:
            pygame.draw.circle(self.screen, color, position, size)
            pygame.draw.circle(self.screen, outline, position, size, 2)

        if is_start or is_end:
            pygame.draw.circle(
                self.screen,
                outline,
                position,
                size + 5,
                3,
            )

            
    def draw_graph(self,
    ) -> None:
        """Draw all connections, then all zones on top of them."""
        for connection in self.graph.connections:
            self.draw_connection(
                connection.zone_a,
                connection.zone_b,
            )

        for zone in self.graph.zones.values():
            self.draw_zone(
                zone,
                is_start=zone.name == self.simulation.start_zone.name,
                is_end=zone.name == self.simulation.end_zone.name,
            )


    def draw_drones(self,visual_positions: dict[int, tuple[float, float]],
    ) -> None:
        """Draw every drone at its animated position with its ID badge."""
        for drone in self.simulation.drones:
            x, y = visual_positions.get(
                drone.drone_id,
                (drone.current_zone.x, drone.current_zone.y),
            )

            position = self.map_to_screen(
                x, y,
            )

            rect = self.drone_image.get_rect(center=position)
            self.screen.blit(self.drone_image, rect)
            self.draw_drone_badge(drone.drone_id, rect.bottomright)


    def draw_drone_badge(self,
        drone_id: int,
        corner: tuple[int, int],
    ) -> None:
        """Draw a small numbered badge at the drone's bottom-right corner."""
        text = self.badge_font.render(str(drone_id), True, (255, 255, 255))

        radius = max(7, text.get_width() // 2 + 3)
        center = (corner[0] - 4, corner[1] - 4)

        pygame.draw.circle(self.screen, (40, 50, 70), center, radius)
        pygame.draw.circle(self.screen, (255, 255, 255), center, radius, 1)
        self.screen.blit(text, text.get_rect(center=center))


    def draw_panel_background(self,
        rect: tuple[int, int, int, int],
    ) -> None:
        """Draw a rounded, semi-transparent white box at rect."""
        left, top, width, height = rect
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(
            panel,
            (255, 255, 255, 190),
            panel.get_rect(),
            border_radius=10,
        )
        self.screen.blit(panel, (left, top))


    def draw_stats_panel(self,
        no_of_drones: int,
        no_of_zones: int,
        turn: int,
        status: str
    ) -> None:
        """Draw drone count, zone count and current turn (top-left)."""
        rows = [
            ("Drones", str(no_of_drones)),
            ("Zones", str(no_of_zones)),
            ("Turn", str(turn)),
            ("Status", status),
        ]

        padding = 12
        row_height = 28
        panel_width = 170
        panel_height = padding * 2 + row_height * len(rows)
        left, top = 20, 20

        self.draw_panel_background((left, top, panel_width, panel_height))

        for i, (label, value) in enumerate(rows):
            y = top + padding + row_height * i + row_height // 2

            label_text = self.font.render(f"{label}:", True, (40, 45, 55))
            self.screen.blit(
                label_text,
                (left + padding, y - label_text.get_height() // 2),
            )

            # Values are right-aligned so the numbers line up.
            value_text = self.font.render(value, True, (40, 45, 55))
            self.screen.blit(
                value_text,
                (
                    left + panel_width - padding - value_text.get_width(),
                    y - value_text.get_height() // 2,
                ),
            )

    def draw_controls_hint(self) -> None:
        """Show the keyboard controls at the bottom center."""
        text = self.font.render(
            "Space:  pause / resume    ·    Esc:  quit",
            True,
            (40, 45, 55),
        )
        padding = 10
        width = text.get_width() + padding * 2
        height = text.get_height() + padding * 2
        left = (self.screen.get_width() - width) // 2
        top = 20

        self.draw_panel_background((left, top, width, height))
        self.screen.blit(text, (left + padding, top + padding))


    def draw_legend(self) -> None:
        """Draw which shape stands for which zone type (bottom-left)."""
        size = 9
        color = (70, 80, 95)
        entries = [
            ("circle", "Normal"),
            ("square", "Restricted"),
            ("diamond", "Priority"),
            ("triangle", "Blocked"),
        ]

        padding = 12
        row_height = 28
        panel_width = 170
        panel_height = padding * 2 + row_height * len(entries)
        left = self.screen.get_width() - panel_width - 20
        top = 20

        self.draw_panel_background((left, top, panel_width, panel_height))

        for i, (shape, label) in enumerate(entries):
            x = left + padding + size
            y = top + padding + row_height * i + row_height // 2

            if shape == "circle":
                pygame.draw.circle(self.screen, color, (x, y), size)
            elif shape == "square":
                pygame.draw.rect(
                    self.screen, color, (x - size, y - size, size * 2, size * 2)
                )
            elif shape == "diamond":
                self.draw_diamond(color, (x, y), size)
            else:
                pygame.draw.polygon(
                    self.screen,
                    color,
                    [(x, y - size), (x + size, y + size), (x - size, y + size)],
                )

            text = self.font.render(label, True, (40, 45, 55))
            self.screen.blit(text, (x + size + 12, y - text.get_height() // 2))


    def draw_map_details(self,
        status: str
    ) -> None:
        """Draw the stats panel and the shape legend."""
        self.draw_stats_panel(len(self.simulation.drones), len(self.graph.zones), self.simulation.turn, status)
        self.draw_legend()
        self.draw_controls_hint()


    def drone_visual_position(self, drone: Drone) -> tuple[float, float]:
        """Return where to draw the drone at the end of a turn.

        A drone flying to a restricted zone is still on the connection
        after its first turn, so it is drawn halfway along it.
        """
        if drone.movement_remaining > 0:
            destination = drone.path[drone.path_index + 1]
            return (
                (drone.current_zone.x + destination.x) / 2,
                (drone.current_zone.y + destination.y) / 2,
            )
        return (drone.current_zone.x, drone.current_zone.y)


    def run_visual(self,
    ) -> None:
        """Animate the simulation turn by turn in a pygame window.

        Each turn is also printed to the terminal, same as without --visual.
        """

        running = True
        paused = False
        clock = pygame.time.Clock()
        simulation_active = True
        animation_duration = 1.0
        turn_pause = 0.6
        animation_progress = 1.0

        start_positions: dict[int, tuple[float, float]] = {}
        target_positions: dict[int, tuple[float, float]] = {}

        last_time = perf_counter()
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        paused = not paused
                elif event.type == pygame.VIDEORESIZE:
                    self.background = self._make_sky_background()
                    self._calculate_map_layout()

            current_time = perf_counter()
            delta_time = current_time - last_time
            last_time = current_time

            if simulation_active and not paused:
                animation_progress += delta_time / animation_duration

                if animation_progress >= 1.0 + turn_pause / animation_duration:
                    if self.simulation.all_drones_finished():
                        simulation_active = False
                    else:
                        # Remember each drone's position before advancing.
                        start_positions = {
                            drone.drone_id: self.drone_visual_position(drone)
                            for drone in self.simulation.drones
                        }

                        if self.simulation.run_turn():
                            target_positions = {
                                drone.drone_id: self.drone_visual_position(drone)
                                for drone in self.simulation.drones
                            }
                            animation_progress = 0.0
                            self.simulation.print_turn()
                        else:
                            simulation_active = False

            self.screen.blit(self.background, (0, 0))
            self.draw_graph()
            # offset_x, offset_y, scale = self.calculate_map_layout(
            #     self.screen, self.graph
            # )

            visual_positions: dict[int, tuple[float, float]] = {}

            for drone in self.simulation.drones:
                drone_id = drone.drone_id

                start = start_positions.get(
                    drone_id,
                    (drone.current_zone.x, drone.current_zone.y),
                )
                target = target_positions.get(drone_id, start)
                t = min(animation_progress, 1.0)
                x = start[0] + (target[0] - start[0]) * t
                y = start[1] + (target[1] - start[1]) * t

                visual_positions[drone_id] = (x, y)

            self.draw_drones(
                visual_positions,
            )

            if self.simulation.all_drones_finished():
                status = "Finished"
            elif paused:
                status = "Paused"
            else:
                status = "Running"

            self.draw_map_details(
                status,
            )

            pygame.display.flip()
            clock.tick(60)
