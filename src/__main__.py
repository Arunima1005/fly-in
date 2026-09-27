from pathlib import Path
from map_selector import MapSelector

def main():
    maps_directory = Path(__file__).resolve().parent.parent / "maps"

    selector = MapSelector(maps_directory)
    difficulty = selector.select_difficulty()
    map_path = selector.select_map(difficulty)

    print(f"\nSelected map: {map_path}")


if __name__ == "__main__":
    main()