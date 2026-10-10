from functools import lru_cache

import pygame

from .model import Drone, Graph, Zone, ZoneType

from pathlib import Path

ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"

def load_drone_image() -> pygame.Surface:
    """Load and scale the drone image."""
    image = pygame.image.load(
        str(ASSET_DIR / "drone.png")
    ).convert_alpha()

    return pygame.transform.smoothscale(image, (24, 24))

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


def calculate_map_layout(
    screen: pygame.Surface,
    graph: Graph,
) -> tuple[int, int, float]:
    xs = [zone.x for zone in graph.zones.values()]
    ys = [zone.y for zone in graph.zones.values()]

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    margin = 100
    available_width = screen.get_width() - 2 * margin
    available_height = screen.get_height() - 2 * margin

    map_width = max_x - min_x
    map_height = max_y - min_y

    scale_x = available_width / map_width if map_width else float("inf")
    scale_y = available_height / map_height if map_height else float("inf")
    scale = min(scale_x, scale_y)
    if scale == float("inf"):
        scale = 1


    map_center_x = (min_x + max_x) / 2
    map_center_y = (min_y + max_y) / 2

    screen_center_x = screen.get_width() / 2
    screen_center_y = screen.get_height() / 2

    offset_x = int(screen_center_x - map_center_x * scale)
    offset_y = int(screen_center_y + map_center_y * scale)

    return offset_x, offset_y, scale


def make_sky_background(width: int, height: int) -> pygame.Surface:
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


def draw_diamond(
    screen: pygame.Surface,
    color: tuple[int, int, int],
    position: tuple[int, int],
    size: int,
) -> None:
    x, y = position

    points = [
        (x, y - size),
        (x + size, y),
        (x, y + size),
        (x - size, y),
    ]

    pygame.draw.polygon(screen, color, points)

def map_to_screen(
    x: int,
    y: int,
    offset_x: int,
    offset_y: int,
    scale: int,
) -> tuple[int, int]:
    screen_x = offset_x + x * scale
    screen_y = offset_y - y * scale

    return screen_x, screen_y


def draw_connection(
    screen: pygame.Surface,
    zone_a: Zone,
    zone_b: Zone,
    offset_x: int,
    offset_y: int,
    scale: int,
) -> None:
    start = map_to_screen(
        zone_a.x,
        zone_a.y,
        offset_x,
        offset_y,
        scale,
    )

    end = map_to_screen(
        zone_b.x,
        zone_b.y,
        offset_x,
        offset_y,
        scale,
    )

    pygame.draw.line(
    screen,
    (60, 75, 95),
    start,
    end,
    2,
)


def draw_zone(
    screen: pygame.Surface,
    zone: Zone,
    offset_x: int,
    offset_y: int,
    scale: float,
    is_start: bool = False,
    is_end: bool = False,
) -> None:
    position = map_to_screen(
        zone.x,
        zone.y,
        offset_x,
        offset_y,
        scale,
    )

    color = PYGAME_ZONE_COLORS.get(
        zone.color or "blue",
        (0, 150, 255),
    )

    size = 20
    outline = (30, 30, 30)
    if zone.zone_type == ZoneType.PRIORITY:
        x, y = position
        draw_diamond(screen, color, position, size)
        pygame.draw.polygon(screen, outline,
                    [(x, y - size), (x + size, y), (x, y + size), (x - size, y)], 2)
    elif zone.zone_type == ZoneType.RESTRICTED:
        pygame.draw.rect(
            screen,
            color,
            (position[0] - size, position[1] - size, size * 2, size * 2),
        )
        pygame.draw.rect(screen, outline,
                    (position[0] - size, position[1] - size, size * 2, size * 2), 2)

    elif zone.zone_type == ZoneType.BLOCKED:
        points = [
            (position[0], position[1] - size),
            (position[0] + size, position[1] + size),
            (position[0] - size, position[1] + size),
        ]
        pygame.draw.polygon(screen, color, points)
        pygame.draw.polygon(screen, outline, points, 2)

    else:
        pygame.draw.circle(screen, color, position, size)
        pygame.draw.circle(screen, outline, position, size, 2)

    if is_start or is_end:
        pygame.draw.circle(
            screen,
            outline,
            position,
            size + 5,
            3,
        )

        
def draw_graph(
    screen: pygame.Surface,
    graph: Graph,
    start_zone: Zone,
    end_zone: Zone,
) -> None:
    offset_x, offset_y, scale = calculate_map_layout(screen, graph)

    for connection in graph.connections:
        draw_connection(
            screen,
            connection.zone_a,
            connection.zone_b,
            offset_x,
            offset_y,
            scale,
        )

    for zone in graph.zones.values():
        draw_zone(
            screen,
            zone,
            offset_x,
            offset_y,
            scale,
            is_start=zone.name == start_zone.name,
            is_end=zone.name == end_zone.name,
        )


def draw_drones(
    screen: pygame.Surface,
    drones: list[Drone],
    offset_x: int,
    offset_y: int,
    scale: float,
    drone_image: pygame.Surface,
    visual_positions: dict[int, tuple[float, float]],
) -> None:
    for drone in drones:
        x, y = visual_positions.get(
            drone.drone_id,
            (drone.current_zone.x, drone.current_zone.y),
        )

        position = map_to_screen(
            x, y, offset_x, offset_y, scale
        )

        rect = drone_image.get_rect(center=position)
        screen.blit(drone_image, rect)
        draw_drone_badge(screen, drone.drone_id, rect.bottomright)


@lru_cache(maxsize=1)
def badge_font() -> pygame.font.Font:
    """Create the badge font once (needs pygame.init() first)."""
    return pygame.font.SysFont(None, 16)


def draw_drone_badge(
    screen: pygame.Surface,
    drone_id: int,
    corner: tuple[int, int],
) -> None:
    """Draw a small numbered badge at the drone's bottom-right corner."""
    text = badge_font().render(str(drone_id), True, (255, 255, 255))

    radius = max(7, text.get_width() // 2 + 3)
    center = (corner[0] - 4, corner[1] - 4)

    pygame.draw.circle(screen, (40, 50, 70), center, radius)
    pygame.draw.circle(screen, (255, 255, 255), center, radius, 1)
    screen.blit(text, text.get_rect(center=center))


def draw_drone_turn(screen: pygame.Surface, ) -> None:
    pass

@lru_cache(maxsize=1)
def details_font() -> pygame.font.Font:
    """Create the font for the info panels once."""
    return pygame.font.SysFont(None, 24)


def draw_panel_background(
    screen: pygame.Surface,
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
    screen.blit(panel, (left, top))


def draw_stats_panel(
    screen: pygame.Surface,
    no_of_drones: int,
    no_of_zones: int,
    turn: int,
    status: str
) -> None:
    """Draw drone count, zone count and current turn (top-left)."""
    font = details_font()
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

    draw_panel_background(screen, (left, top, panel_width, panel_height))

    for i, (label, value) in enumerate(rows):
        y = top + padding + row_height * i + row_height // 2

        label_text = font.render(f"{label}:", True, (40, 45, 55))
        screen.blit(
            label_text,
            (left + padding, y - label_text.get_height() // 2),
        )

        # Values are right-aligned so the numbers line up.
        value_text = font.render(value, True, (40, 45, 55))
        screen.blit(
            value_text,
            (
                left + panel_width - padding - value_text.get_width(),
                y - value_text.get_height() // 2,
            ),
        )


def draw_legend(screen: pygame.Surface) -> None:
    """Draw which shape stands for which zone type (bottom-left)."""
    font = details_font()
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
    left = screen.get_width() - panel_width - 20
    top = 20

    draw_panel_background(screen, (left, top, panel_width, panel_height))

    for i, (shape, label) in enumerate(entries):
        x = left + padding + size
        y = top + padding + row_height * i + row_height // 2

        if shape == "circle":
            pygame.draw.circle(screen, color, (x, y), size)
        elif shape == "square":
            pygame.draw.rect(
                screen, color, (x - size, y - size, size * 2, size * 2)
            )
        elif shape == "diamond":
            draw_diamond(screen, color, (x, y), size)
        else:
            pygame.draw.polygon(
                screen,
                color,
                [(x, y - size), (x + size, y + size), (x - size, y + size)],
            )

        text = font.render(label, True, (40, 45, 55))
        screen.blit(text, (x + size + 12, y - text.get_height() // 2))


def draw_map_details(
    screen: pygame.Surface,
    no_of_drones: int,
    no_of_zones: int,
    turn: int,
    status: str
) -> None:
    """Draw the stats panel and the shape legend."""
    draw_stats_panel(screen, no_of_drones, no_of_zones, turn, status)
    draw_legend(screen)
