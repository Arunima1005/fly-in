
from pathlib import Path

import pygame


class MapSelectionUI:
    """Select a difficulty and map using Pygame."""

    DIFFICULTIES = ["easy", "medium", "hard", "challenger"]

    def __init__(self, screen: pygame.Surface) -> None:
        """Store the window and prepare fonts and button colors."""
        self.screen = screen
        self.font = pygame.font.SysFont(None, 36)
        self.title_font = pygame.font.SysFont(None, 52)
        self.clock = pygame.time.Clock()
        self.background = (225, 238, 248)
        self.button_color = (60, 100, 150)
        self.button_hover_color = (40, 75, 120)
        self.text_color = (255, 255, 255)

    def draw_button(
        self,
        text: str,
        rect: pygame.Rect,
        mouse_position: tuple[int, int],
    ) -> None:
        """Draw a button and highlight it when hovered over."""
        color = (
            self.button_hover_color
            if rect.collidepoint(mouse_position)
            else self.button_color
        )
        pygame.draw.rect(self.screen, color, rect, border_radius=8)

        label = self.font.render(text, True, self.text_color)
        self.screen.blit(label, label.get_rect(center=rect.center))

    def select_map(self, maps_directory: Path) -> Path | None:
        """Display the difficulty screen followed by the map screen."""
        selected_difficulty = None
        buttons: list[tuple[str, pygame.Rect, Path | None]] = []
        running = True
        mouse_position = (0, 0)

        while running:
            width, height = self.screen.get_size()
            self.screen.fill(self.background)

            # Difficulty buttons have no map file (None), map buttons do.
            options: list[tuple[str, Path | None]]
            if selected_difficulty is None:
                title = "Select Difficulty"
                options = [
                    (name.title(), None)
                    for name in self.DIFFICULTIES
                ]
            else:
                title = f"Select {selected_difficulty.title()} Map"
                difficulty_directory = maps_directory / selected_difficulty
                maps = sorted(difficulty_directory.glob("*.txt"))
                options = [(path.name, path) for path in maps]
                options.append(("Back", None))

            title_surface = self.title_font.render(
                title, True, (35, 50, 70)
            )
            self.screen.blit(
                title_surface,
                title_surface.get_rect(center=(width // 2, 100)),
            )

            buttons = []
            button_width = min(420, width - 80)
            button_height = 55
            gap = 15
            total_height = len(options) * (button_height + gap) - gap
            start_y = max(160, (height - total_height) // 2)

            for index, (label, map_path) in enumerate(options):
                rect = pygame.Rect(
                    (width - button_width) // 2,
                    start_y + index * (button_height + gap),
                    button_width,
                    button_height,
                )
                buttons.append((label, rect, map_path))
                self.draw_button(label, rect, mouse_position)

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if selected_difficulty is not None:
                            selected_difficulty = None
                        else:
                            return None

                if event.type == pygame.MOUSEMOTION:
                    mouse_position = event.pos

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button != 1:
                        continue

                    for label, rect, map_path in buttons:
                        if not rect.collidepoint(event.pos):
                            continue

                        if selected_difficulty is None:
                            selected_difficulty = label.lower()
                        elif label == "Back":
                            selected_difficulty = None
                        elif map_path is not None:
                            return map_path

            self.clock.tick(60)

        return None
