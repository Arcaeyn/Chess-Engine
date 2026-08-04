import pygame
import sys

# ============================================================
# Piece-Square Table Editor
#
# Board indexing:
#   a1 = 0, b1 = 1, ..., h1 = 7
#   a2 = 8, ..., h8 = 63
#
# Controls:
#   Left-click square      Select it
#   Type number            Replace its value
#   Enter                  Commit typed value
#   Escape                 Cancel typing
#   Arrow keys             Move selection
#   Backspace              Delete typed character
#   C                      Clear all values
#   P                      Print both tables in the terminal
#
# Black table is produced by vertically mirroring the white table:
#   rank 1 <-> rank 8, rank 2 <-> rank 7, etc.
# ============================================================

pygame.init()

WIDTH = 920
HEIGHT = 760
BOARD_SIZE = 640
SQUARE_SIZE = BOARD_SIZE // 8
BOARD_X = 40
BOARD_Y = 60
PANEL_X = BOARD_X + BOARD_SIZE + 30

FPS = 60

LIGHT_SQUARE = (235, 236, 208)
DARK_SQUARE = (119, 149, 86)
SELECTED = (246, 246, 105)
GRID = (40, 40, 40)
TEXT = (25, 25, 25)
PANEL_BG = (238, 238, 238)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
POSITIVE = (65, 145, 255)
NEGATIVE = (235, 75, 75)
ZERO = (225, 225, 225)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Piece-Square Table Editor")
clock = pygame.time.Clock()

font = pygame.font.Font(None, 27)
small_font = pygame.font.Font(None, 21)
large_font = pygame.font.Font(None, 34)

values = [0] * 64
selected_square = 0
input_buffer = ""


def square_to_board_position(square: int) -> tuple[int, int]:
    """Convert square index (a1=0) to visible board row and column."""
    rank = square // 8
    file = square % 8

    screen_row = 7 - rank
    screen_col = file
    return screen_row, screen_col


def board_position_to_square(row: int, col: int) -> int:
    """Convert visible board row and column to square index."""
    rank = 7 - row
    file = col
    return rank * 8 + file


def square_name(square: int) -> str:
    file = square % 8
    rank = square // 8 + 1
    return f"{chr(ord('a') + file)}{rank}"


def mirror_for_black(table: list[int]) -> list[int]:
    """
    Mirror ranks vertically for Black.

    This preserves files:
      a1 <-> a8
      b1 <-> b8
      ...
    """
    mirrored = [0] * 64

    for square, value in enumerate(table):
        mirrored[square ^ 56] = value

    return mirrored


def table_as_python(name: str, table: list[int]) -> str:
    lines = [f"{name} = ["]
    for rank in range(8):
        start = rank * 8
        row = table[start:start + 8]
        formatted = ", ".join(f"{value:4d}" for value in row)
        lines.append(f"    {formatted},")
    lines.append("]")
    return "\n".join(lines)


def print_tables() -> None:
    black_values = mirror_for_black(values)

    print("\n" + "=" * 72)
    print("Square order: a1, b1, ..., h1, a2, ..., h8")
    print("=" * 72)
    print(table_as_python("WHITE_TABLE", values))
    print()
    print(table_as_python("BLACK_TABLE", black_values))
    print("=" * 72 + "\n")


def blend(base: tuple[int, int, int], overlay: tuple[int, int, int], amount: float):
    amount = max(0.0, min(1.0, amount))
    return tuple(
        int(base[i] * (1.0 - amount) + overlay[i] * amount)
        for i in range(3)
    )


def score_color(base_color, value: int):
    if value == 0:
        return base_color

    strength = min(abs(value) / 100.0, 1.0) * 0.65
    target = POSITIVE if value > 0 else NEGATIVE
    return blend(base_color, target, strength)


def commit_input():
    global input_buffer

    if input_buffer in ("", "-"):
        input_buffer = ""
        return

    try:
        values[selected_square] = int(input_buffer)
    except ValueError:
        pass

    input_buffer = ""


def move_selection(file_change: int, rank_change: int):
    global selected_square

    commit_input()

    file = selected_square % 8
    rank = selected_square // 8

    file = max(0, min(7, file + file_change))
    rank = max(0, min(7, rank + rank_change))

    selected_square = rank * 8 + file


def draw_board():
    for row in range(8):
        for col in range(8):
            square = board_position_to_square(row, col)
            x = BOARD_X + col * SQUARE_SIZE
            y = BOARD_Y + row * SQUARE_SIZE

            base = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
            color = score_color(base, values[square])

            pygame.draw.rect(
                screen,
                color,
                (x, y, SQUARE_SIZE, SQUARE_SIZE),
            )

            if square == selected_square:
                pygame.draw.rect(
                    screen,
                    SELECTED,
                    (x + 2, y + 2, SQUARE_SIZE - 4, SQUARE_SIZE - 4),
                    5,
                )

            displayed_value = (
                input_buffer
                if square == selected_square and input_buffer != ""
                else str(values[square])
            )

            value_surface = font.render(displayed_value, True, TEXT)
            value_rect = value_surface.get_rect(
                center=(x + SQUARE_SIZE // 2, y + SQUARE_SIZE // 2)
            )
            screen.blit(value_surface, value_rect)

            index_surface = small_font.render(str(square), True, TEXT)
            screen.blit(index_surface, (x + 5, y + 4))

            pygame.draw.rect(
                screen,
                GRID,
                (x, y, SQUARE_SIZE, SQUARE_SIZE),
                1,
            )

    # File labels
    for file in range(8):
        label = small_font.render(chr(ord("a") + file), True, TEXT)
        x = BOARD_X + file * SQUARE_SIZE + SQUARE_SIZE // 2
        screen.blit(label, label.get_rect(center=(x, BOARD_Y + BOARD_SIZE + 18)))

    # Rank labels
    for rank in range(8):
        label = small_font.render(str(8 - rank), True, TEXT)
        y = BOARD_Y + rank * SQUARE_SIZE + SQUARE_SIZE // 2
        screen.blit(label, label.get_rect(center=(BOARD_X - 18, y)))


def draw_panel():
    pygame.draw.rect(
        screen,
        PANEL_BG,
        (PANEL_X, BOARD_Y, WIDTH - PANEL_X - 20, BOARD_SIZE),
        border_radius=8,
    )

    selected_name = square_name(selected_square)
    selected_value = values[selected_square]

    lines = [
        ("PST Editor", large_font),
        ("", small_font),
        (f"Selected: {selected_name}", font),
        (f"Index: {selected_square}", font),
        (f"Value: {selected_value}", font),
        ("", small_font),
        ("Type a number", small_font),
        ("Enter: commit", small_font),
        ("Arrows: move", small_font),
        ("Esc: cancel", small_font),
        ("C: clear all", small_font),
        ("P: print tables", small_font),
        ("", small_font),
        ("Blue = positive", small_font),
        ("Red = negative", small_font),
        ("", small_font),
        ("Black table uses", small_font),
        ("vertical rank mirror.", small_font),
    ]

    y = BOARD_Y + 18
    for text, text_font in lines:
        if text:
            surface = text_font.render(text, True, TEXT)
            screen.blit(surface, (PANEL_X + 16, y))
        y += 29 if text_font == font else 24


def handle_mouse_click(position):
    global selected_square, input_buffer

    mouse_x, mouse_y = position

    if not (
        BOARD_X <= mouse_x < BOARD_X + BOARD_SIZE
        and BOARD_Y <= mouse_y < BOARD_Y + BOARD_SIZE
    ):
        return

    commit_input()

    col = (mouse_x - BOARD_X) // SQUARE_SIZE
    row = (mouse_y - BOARD_Y) // SQUARE_SIZE
    selected_square = board_position_to_square(row, col)
    input_buffer = ""


def main():
    global selected_square, input_buffer, values

    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_mouse_click(event.pos)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    commit_input()

                elif event.key == pygame.K_ESCAPE:
                    input_buffer = ""

                elif event.key == pygame.K_BACKSPACE:
                    input_buffer = input_buffer[:-1]

                elif event.key == pygame.K_LEFT:
                    move_selection(-1, 0)

                elif event.key == pygame.K_RIGHT:
                    move_selection(1, 0)

                elif event.key == pygame.K_UP:
                    move_selection(0, 1)

                elif event.key == pygame.K_DOWN:
                    move_selection(0, -1)

                elif event.key == pygame.K_c:
                    values = [0] * 64
                    input_buffer = ""

                elif event.key == pygame.K_p:
                    commit_input()
                    print_tables()

                elif event.unicode.isdigit():
                    input_buffer += event.unicode

                elif event.unicode == "-" and input_buffer == "":
                    input_buffer = "-"

        screen.fill(WHITE)
        draw_board()
        draw_panel()

        footer = small_font.render(
            "Press P to print copy-ready Python lists in the terminal.",
            True,
            TEXT,
        )
        screen.blit(footer, (BOARD_X, HEIGHT - 34))

        pygame.display.flip()
        clock.tick(FPS)

    print_tables()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
