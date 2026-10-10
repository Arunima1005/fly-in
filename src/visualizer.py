"""Pygame visualization of the simulation (enabled with --visual)."""
from time import perf_counter

import pygame

from .model import Drone, Graph, Zone
from .simulation import Simulation
from .ui import (
    calculate_map_layout,
    draw_drones,
    draw_graph,
    load_drone_image,
    make_sky_background,
    draw_map_details,
)


def drone_visual_position(drone: Drone) -> tuple[float, float]:
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


def run_visual(
    simulation: Simulation,
    graph: Graph,
    start_zone: Zone,
    end_zone: Zone,
) -> None:
    """Animate the simulation turn by turn in a pygame window.

    Each turn is also printed to the terminal, same as without --visual.
    """
    pygame.init()

    screen = pygame.display.set_mode((1600, 1000))
    pygame.display.set_caption("Fly-in")

    background = make_sky_background(*screen.get_size())
    drone_image = load_drone_image()

    running = True
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
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        current_time = perf_counter()
        delta_time = current_time - last_time
        last_time = current_time

        if simulation_active:
            animation_progress += delta_time / animation_duration

            if animation_progress >= 1.0 + turn_pause / animation_duration:
                if simulation.all_drones_finished():
                    simulation_active = False
                else:
                    # Remember each drone's position before advancing.
                    start_positions = {
                        drone.drone_id: drone_visual_position(drone)
                        for drone in simulation.drones
                    }

                    if simulation.run_turn():
                        target_positions = {
                            drone.drone_id: drone_visual_position(drone)
                            for drone in simulation.drones
                        }
                        animation_progress = 0.0
                        simulation.print_turn()
                    else:
                        simulation_active = False

        screen.blit(background, (0, 0))
        draw_graph(screen, graph, start_zone, end_zone)
        offset_x, offset_y, scale = calculate_map_layout(
            screen, graph
        )

        visual_positions: dict[int, tuple[float, float]] = {}

        for drone in simulation.drones:
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

        draw_drones(
            screen,
            simulation.drones,
            offset_x,
            offset_y,
            scale,
            drone_image,
            visual_positions,
        )
        draw_map_details(
            screen,
            len(simulation.drones),
            len(graph.zones),
            simulation.turn,
        )

        pygame.display.flip()
        clock.tick(60)
    pygame.quit()
