from pathlib import Path
from map_selector import MapSelector
from parse import MapParser

def main():
    maps_directory = Path(__file__).resolve().parent.parent / "maps"

    selector = MapSelector(maps_directory)
    difficulty = selector.select_difficulty()
    map_path = selector.select_map(difficulty)

    print(f"\nSelected map: {map_path}")
    mp = MapParser()
    mp.parse_file(map_path)


if __name__ == "__main__":
    main()