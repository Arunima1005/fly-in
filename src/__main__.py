from pathlib import Path

from .model import Drone
from .simulation import Simulation
from .map_selector import MapSelector
from .parse import MapParser, ParserError


def main() -> None:
    maps_directory = Path(__file__).resolve().parent.parent / "maps"

    selector = MapSelector(maps_directory)
    difficulty = selector.select_difficulty()
    map_path = selector.select_map(difficulty)

    mp = MapParser()
    try:
        mp.parse_file(map_path)
    except ParserError as error:
        print(f"Error: {error}")
        return
    print(mp.graph)
    print(mp.nb_drones)
    
    start_zone = mp.start_zone

    if start_zone is None:
        raise ValueError("Start zone not found")
    
    end_zone = mp.end_zone
    if end_zone is None:
        raise ValueError("Goal zone not found")

    drones: list[Drone] = []
    for drone_id in range(mp.nb_drones):
        drone = Drone(
            drone_id=drone_id,
            current_zone=start_zone,
            path_index=0,
        )
        drones.append(drone)
    simulation = Simulation(
        mp.graph,
        drones,
        end_zone,
        start_zone,
    )

    simulation.run()


if __name__ == "__main__":
    main()
