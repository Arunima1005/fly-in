from pathlib import Path


class MapSelector:
    """Handle difficulty and map selection."""
    DEFAULT_DIRECTORY = Path(__file__).resolve().parent.parent / "maps"

    def __init__(self, maps_directory: Path):
        """Store the folder that holds the difficulty subfolders."""
        self.maps_directory = maps_directory

    def select_difficulty(self) -> str:
        """Ask the user to select a difficulty level."""
        difficulties = {
            "1": "easy",
            "2": "medium",
            "3": "hard",
            "4": "challenger",
        }

        while True:
            print("\n Select map difficulty level:")
            print("1. Easy")
            print("2. Medium")
            print("3. Hard")
            print("4. Challenger")

            difficulty_level = input("Choice: ").strip()

            if difficulty_level in difficulties:
                return difficulties[difficulty_level]

            print("Invalid choice. Please select 1-4 level.")

    def select_map(self, diffculty_level: str) -> Path:
        """Ask the user to select a map for the given difficulty."""
        difficulty_directory = self.maps_directory / diffculty_level

        maps = sorted(difficulty_directory.glob("*.txt"))

        if not maps:
            raise FileNotFoundError(
                f"No maps found for difficulty: {diffculty_level}"
                )

        while True:
            print(f"\nAvailable {diffculty_level} maps:")

            for index, map_path in enumerate(maps, start=1):
                print(f"{index}. {map_path.name}")

            choice = input("Choice: ").strip()

            if choice.isdigit():
                index = int(choice)

                if 1 <= index <= len(maps):
                    return maps[index - 1]

            print("Invalid choice.")
