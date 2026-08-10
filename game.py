import pygame
import time
import math

from gameLogic.board import GameState, Move
from bot.bot import Bot

pygame.init()
pygame.mixer.init()


WIDTH = 900
HEIGHT = 800

BOARDSIZE = 700
SQUARESIZE = BOARDSIZE // 8
PADDING = SQUARESIZE // 15

LIGHT = (232, 239, 255)
DARK = (120, 142, 191)
HIGHLIGHT = (80, 80, 120)
BORDER = (80, 80, 120)

font = pygame.font.Font(None, 28)
moveSound = pygame.mixer.Sound("assets/sounds/move-self.mp3")
game_state = GameState()
bot1 = Bot(game_state)
bot2 = Bot(game_state)
bot2.useAspirationWindow = True

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess Engine")


def loadPieceImage(filename):
    image = pygame.image.load(
        f"assets/pieces-basic-png/{filename}"
    ).convert_alpha()

    piece_size = SQUARESIZE - PADDING * 2

    return pygame.transform.smoothscale(
        image,
        (piece_size, piece_size),
    )

PIECE_IMAGES = {
    "white_pawns": loadPieceImage("white-pawn.png"),
    "white_rooks": loadPieceImage("white-rook.png"),
    "white_knights": loadPieceImage("white-knight.png"),
    "white_bishops": loadPieceImage("white-bishop.png"),
    "white_queens": loadPieceImage("white-queen.png"),
    "white_kings": loadPieceImage("white-king.png"),

    "black_pawns": loadPieceImage("black-pawn.png"),
    "black_rooks": loadPieceImage("black-rook.png"),
    "black_knights": loadPieceImage("black-knight.png"),
    "black_bishops": loadPieceImage("black-bishop.png"),
    "black_queens": loadPieceImage("black-queen.png"),
    "black_kings": loadPieceImage("black-king.png"),
}

def drawBoard():
    board_x = (WIDTH - BOARDSIZE) // 2
    board_y = (HEIGHT - BOARDSIZE) // 2
    margin = (SQUARESIZE * 8)*1.015 - (SQUARESIZE * 8)
    rect = pygame.Rect(
                board_x - margin//2,
                board_y - margin//2,
                (SQUARESIZE * 8) + margin,
                (SQUARESIZE * 8) + margin,
            )


    pygame.draw.rect(screen, BORDER, rect)

    for screen_rank in range(8):
        rank_label = font.render(
            str(8 - screen_rank),
            True,
            DARK if screen_rank % 2 == 0 else LIGHT,
        )

        for screen_file in range(8):
            color = (
                LIGHT
                if (screen_rank + screen_file) % 2 == 0
                else DARK
            )

            rect = pygame.Rect(
                board_x + screen_file * SQUARESIZE,
                board_y + screen_rank * SQUARESIZE,
                SQUARESIZE,
                SQUARESIZE,
            )

            pygame.draw.rect(screen, color, rect)

        screen.blit(
            rank_label,
            (
                board_x + PADDING,
                board_y + screen_rank * SQUARESIZE + PADDING,
            ),
        )

    for screen_file in range(8):
        file_label = font.render(
            "abcdefgh"[screen_file],
            True,
            LIGHT if screen_file % 2 == 0 else DARK,
        )

        screen.blit(
            file_label,
            (
                board_x
                + screen_file * SQUARESIZE
                + SQUARESIZE
                - PADDING * 3,
                board_y + BOARDSIZE - PADDING * 5,
            ),
        )

def createCircleSurface(radius, color):
    diameter = radius * 2

    circle_surface = pygame.Surface(
        (diameter, diameter),
        pygame.SRCALPHA,
    )

    pygame.draw.circle(
        circle_surface,
        color,
        (radius, radius),
        radius,
    )

    return circle_surface

def highlightBitboard(bitboard):
    board_x = (WIDTH - BOARDSIZE) // 2
    board_y = (HEIGHT - BOARDSIZE) // 2

    highlight = createCircleSurface(
        SQUARESIZE // 6,
        (80, 80, 80),
    )

    while bitboard:
        square = (bitboard & -bitboard).bit_length() - 1

        screen_file = square % 8
        chess_rank = square // 8
        screen_rank = 7 - chess_rank

        x = (
            board_x
            + screen_file * SQUARESIZE
            + SQUARESIZE // 3
        )

        y = (
            board_y
            + screen_rank * SQUARESIZE
            + SQUARESIZE // 3
        )

        screen.blit(
            highlight,
            (x, y),
            special_flags=pygame.BLEND_RGB_SUB,
        )

        bitboard &= bitboard - 1

def highlightSquare(rank, file, width=SQUARESIZE//17, color=HIGHLIGHT):
    board_x = (WIDTH - BOARDSIZE) // 2
    board_y = (HEIGHT - BOARDSIZE) // 2

    screen_file = file - 1
    screen_rank = 8 - rank

    rect = pygame.Rect(
        board_x + screen_file * SQUARESIZE,
        board_y + screen_rank * SQUARESIZE,
        SQUARESIZE,
        SQUARESIZE,
    )

    pygame.draw.rect(
        screen,
        color,
        rect,
        width
        
    )

def displayCheckmate():
    bRank, bFile = game_state.bitboardToSquare(game_state.black_kings)
    wRank, wFile = game_state.bitboardToSquare(game_state.white_kings)

    if game_state.white_to_move:
        highlightSquare(wRank, wFile, SQUARESIZE, (200, 80, 80))
        highlightSquare(bRank, bFile, SQUARESIZE, (80, 200, 80))

    else:
        highlightSquare(bRank, bFile, SQUARESIZE, (200, 80, 80))
        highlightSquare(wRank, wFile, SQUARESIZE, (80, 200, 80))

def traverseMoves(game_state):
    curr = -2
    pass

def displayDraw():
    bRank, bFile = game_state.bitboardToSquare(game_state.black_kings)
    wRank, wFile = game_state.bitboardToSquare(game_state.white_kings)

    highlightSquare(wRank, wFile, SQUARESIZE, (140, 140, 140))
    highlightSquare(bRank, bFile, SQUARESIZE, (140, 140, 140))

def drawText(text, x, y, color=(255, 255, 255)):
    surface = font.render(str(text), True, color)
    screen.blit(surface, (x, y))

def drawPieces():
    board_x = (WIDTH - BOARDSIZE) // 2
    board_y = (HEIGHT - BOARDSIZE) // 2

    for bitboard_name, image in PIECE_IMAGES.items():
        bitboard = getattr(game_state, bitboard_name)

        while bitboard:
            piece_bit = bitboard & -bitboard
            square = piece_bit.bit_length() - 1

            screen_file = square % 8
            chess_rank = square // 8
            screen_rank = 7 - chess_rank

            x = (
                board_x
                + screen_file * SQUARESIZE
                + PADDING
            )

            y = (
                board_y
                + screen_rank * SQUARESIZE
                + PADDING
            )

            screen.blit(image, (x, y))

            bitboard &= bitboard - 1

def mouseToSquare(mouse_x, mouse_y):
    board_x = (WIDTH - BOARDSIZE) // 2
    board_y = (HEIGHT - BOARDSIZE) // 2

    relative_x = mouse_x - board_x
    relative_y = mouse_y - board_y

    if not (0 <= relative_x < BOARDSIZE):
        return None

    if not (0 <= relative_y < BOARDSIZE):
        return None

    file = relative_x // SQUARESIZE + 1
    rank = 8 - relative_y // SQUARESIZE

    return rank, file

def evalBar(eval):
    board_x = (WIDTH - BOARDSIZE) // 2
    board_y = (HEIGHT - BOARDSIZE) // 2

    padding = SQUARESIZE//3
    border_radius = SQUARESIZE //20
    width = SQUARESIZE//6
    black_percent = 1 - (1.0 / (1.0 + math.exp(-eval / 225.0)))

    border = pygame.Rect(
        board_x - padding - border_radius,
        board_y - border_radius,
        width + border_radius * 2,
        SQUARESIZE * 8 + border_radius * 2,
    )

    back = pygame.Rect(
        board_x - padding,
        board_y,
        width,
        SQUARESIZE * 8,
    )
    rect = pygame.Rect(
        board_x - padding,
        board_y,
        width,
        min(BOARDSIZE * black_percent, BOARDSIZE - border_radius)
    )

    pygame.draw.rect(screen, HIGHLIGHT, border)
    pygame.draw.rect(screen, LIGHT, back)
    pygame.draw.rect(screen, DARK, rect)
    sign = "+" if eval > 0 else ""
    drawText(sign + str(round(eval/100, 2)), board_x - padding - border_radius * 4, board_y + BOARDSIZE + border_radius)

clock = pygame.time.Clock()

running = True
selected = False

selected_rank = None
selected_file = None

last_move = None
start = 0
end = 0


while running:
    checkmate = game_state.isCheckmate()
    if not game_state.white_to_move and not checkmate:
        start = time.time()
        move = bot2.findMoveToggle(5)
        if move is not None:
            last_move = move
            game_state.movePiece(move)
            moveSound.play()
            static_eval = bot2.evaluator.evaluate(game_state)
            print("Current-position evaluation:", static_eval)
            print("Depth-search evaluation:", bot2.eval)
            end = time.time()  


    best = bot2.eval
    # Handeling keyboard inputs
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            # Reset Board
            if event.key == pygame.K_r:
                game_state.resetBoard()

                selected = False
                selected_rank = None
                selected_file = None
                last_move = None

            # Undo Move
            if event.key == pygame.K_LEFT:

                # We need to check if there are any moves for us to undo 
                if last_move and len(game_state.move_history) >= 1:
                    last_move = game_state.move_history[-1]
                    game_state.undoMove(last_move)


    
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button != 1:
                continue

            clicked_square = mouseToSquare(*event.pos)

            if clicked_square is None:
                selected = False
                continue

            clicked_rank, clicked_file = clicked_square

            # Nothing is currently selected.
            if not selected:
                expected_color = "w" if game_state.white_to_move else "b"

                clicked_color = game_state.pieceColor(
                    clicked_rank,
                    clicked_file,
                )

                if clicked_color == expected_color:
                    selected_rank = clicked_rank
                    selected_file = clicked_file
                    selected = True

            # A piece is already selected, so create a Move.
            else:
                # If a pawn is promoting we need to make it a queen
                piece = game_state.getPiece(selected_rank, selected_file)
                if "pawn" in piece and (clicked_rank == 8 or clicked_rank == 1):
                    move = Move(
                        start_rank=selected_rank,
                        start_file=selected_file,
                        end_rank=clicked_rank,
                        end_file=clicked_file,
                        promotion=piece[:5] + "_queens"
                )
                # Otherwise we can just make a nomral move
                else:
                    move = Move(
                        start_rank=selected_rank,
                        start_file=selected_file,
                        end_rank=clicked_rank,
                        end_file=clicked_file)


                # Clicking the selected square deselects it.
                if (
                    move.start_rank == move.end_rank
                    and move.start_file == move.end_file
                ):
                    selected = False
                    continue

                if game_state.moveIsLegal(move):
                    game_state.movePiece(move)
                    moveSound.play()
                    last_move = move

                selected = False

    screen.fill((30, 30, 40))
    drawBoard()

    if last_move is not None:
        highlightSquare(
            last_move.start_rank,
            last_move.start_file,
        )

        highlightSquare(
            last_move.end_rank,
            last_move.end_file,
        )

    if selected:
        pseudo_legal_moves = game_state.getLegalMoves(
            selected_rank,
            selected_file,
        )

        highlightBitboard(pseudo_legal_moves)

        highlightSquare(
            selected_rank,
            selected_file,
        )

    if game_state.isCheckmate():
            displayCheckmate()

    drawPieces()


    turn_text = (
        "White"
        if game_state.white_to_move
        else "Black"
    )

    turn_label = font.render(
        turn_text,
        True,
        (255, 255, 255),
    )

    screen.blit(turn_label, (100, 20))
    
    drawText("Depth: " + str(5) + "  Time: "  + str(round((end - start), 2)) + "s", 610, 20)
    evalBar(best)
    if not game_state.white_to_move:
        print(str(round((end - start), 2)))

    pygame.display.flip()
    clock.tick(60)


pygame.quit()