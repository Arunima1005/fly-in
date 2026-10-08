import pygame

from .model import Graph, Zone

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
        (100, 100, 100),
        start,
        end,
        3,
    )


def draw_zone(
    screen: pygame.Surface,
    zone: Zone,
    offset_x: int,
    offset_y: int,
    scale: int,
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

    pygame.draw.circle(
        screen,
        color,
        position,
        25,
    )

def draw_graph(
    screen: pygame.Surface,
    graph: Graph,
) -> None:
    xs = [zone.x for zone in graph.zones.values()]
    ys = [zone.y for zone in graph.zones.values()]

    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)

    margin = 100

    map_width = max_x - min_x
    map_height = max_y - min_y

    available_width = screen.get_width() - 2 * margin
    available_height = screen.get_height() - 2 * margin

    scale_x = available_width / map_width if map_width else 1
    scale_y = available_height / map_height if map_height else 1

    scale = min(scale_x, scale_y)

    map_center_x = (min_x + max_x) / 2
    map_center_y = (min_y + max_y) / 2

    screen_center_x = screen.get_width() / 2
    screen_center_y = screen.get_height() / 2

    offset_x = int(screen_center_x - map_center_x * scale)
    offset_y = int(screen_center_y + map_center_y * scale)

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
        )