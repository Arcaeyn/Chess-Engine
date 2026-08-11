from gameLogic.board import GameState, Move
from bot.bot import Bot
import pygame
import math
import time

# Initialize
pygame.init()
pygame.mixer.init()

# Constants
WIDTH = 900
HEIGHT = 800

BOARDSIZE = 700
SQUARESIZE = BOARDSIZE // 8
PADDING = SQUARESIZE // 15

LIGHT = (232, 239, 255)
DARK = (120, 142, 191)
HIGHLIGHT = (80, 80, 120)
BORDER = (80, 80, 120)
       
# Creating a class to handle all graphical user interface aspects
class Gui:
    def __init__(self, game : GameState, bot : Bot):
        # Chess Objects
        self.game = game
        self.bot = bot

        # GUI aspects
        self.width = WIDTH
        self.height = HEIGHT
        self.board_size = BOARDSIZE
        self.square_size = self.board_size//8
        self.padding = self.square_size//15

        # Game State objects
        self.running = True
        self.selected_square = None

        # Colors
        self.light = LIGHT
        self.dark = DARK
        self.highlight = HIGHLIGHT
        self.border = BORDER
        self.background = ((30, 30, 40))

        # Initialize font, sounds, and screen
        self.font = pygame.font.Font(None, 28)
        self.move_sound = pygame.mixer.Sound("assets/sounds/move-self.mp3")
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Chess Engine")

        # Piece images
        self.piece_images = {
    "white_pawns": self.loadPieceImage("white-pawn.png"),
    "white_rooks": self.loadPieceImage("white-rook.png"),
    "white_knights": self.loadPieceImage("white-knight.png"),
    "white_bishops": self.loadPieceImage("white-bishop.png"),
    "white_queens": self.loadPieceImage("white-queen.png"),
    "white_kings": self.loadPieceImage("white-king.png"),

    "black_pawns": self.loadPieceImage("black-pawn.png"),
    "black_rooks": self.loadPieceImage("black-rook.png"),
    "black_knights": self.loadPieceImage("black-knight.png"),
    "black_bishops": self.loadPieceImage("black-bishop.png"),
    "black_queens": self.loadPieceImage("black-queen.png"),
    "black_kings": self.loadPieceImage("black-king.png"),
}


    # Helper functions for drawing our board
    def loadPieceImage(self, filename):
        image = pygame.image.load(
            f"assets/pieces-basic-png/{filename}"
        ).convert_alpha()

        piece_size = self.square_size - self.padding * 2

        return pygame.transform.smoothscale(
            image,
            (piece_size, piece_size),
        )

    def drawBoard(self):
        board_x = (self.width - self.board_size) // 2
        board_y = (self.height - self.board_size) // 2
        margin = (self.square_size * 8)*1.015 - (self.square_size * 8)
        rect = pygame.Rect(
                    board_x - margin//2,
                    board_y - margin//2,
                    (self.square_size * 8) + margin,
                    (self.square_size * 8) + margin,
                )


        pygame.draw.rect(self.screen, self.border, rect)

        for screen_rank in range(8):
            rank_label = self.font.render(
                str(8 - screen_rank),
                True,
                self.dark if screen_rank % 2 == 0 else self.light,
            )

            for screen_file in range(8):
                color = (
                    self.light
                    if (screen_rank + screen_file) % 2 == 0
                    else self.dark
                )

                rect = pygame.Rect(
                    board_x + screen_file * self.square_size,
                    board_y + screen_rank * self.square_size,
                    self.square_size,
                    self.square_size,
                )

                pygame.draw.rect(self.screen, color, rect)

            self.screen.blit(
                rank_label,
                (
                    board_x + self.padding,
                    board_y + screen_rank * self.square_size + self.padding,
                ),
            )

        for screen_file in range(8):
            file_label = self.font.render(
                "abcdefgh"[screen_file],
                True,
                self.light if screen_file % 2 == 0 else self.dark,
            )

            self.screen.blit(
                file_label,
                (
                    board_x
                    + screen_file * self.square_size
                    + self.square_size
                    - self.padding * 3,
                    board_y + self.board_size - self.padding * 5,
                ),
            )

    def createCircleSurface(self, radius, color):
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

    def highlightBitboard(self, bitboard):
        board_x = (self.width - self.board_size) // 2
        board_y = (self.height - self.board_size) // 2

        highlight = self.createCircleSurface(
            self.square_size // 6,
            (80, 80, 80),
        )

        while bitboard:
            square = (bitboard & -bitboard).bit_length() - 1

            screen_file = square % 8
            chess_rank = square // 8
            screen_rank = 7 - chess_rank

            x = (
                board_x
                + screen_file * self.square_size
                + self.square_size // 3
            )

            y = (
                board_y
                + screen_rank * self.square_size
                + self.square_size // 3
            )

            self.screen.blit(
                highlight,
                (x, y),
                special_flags=pygame.BLEND_RGB_SUB,
            )

            bitboard &= bitboard - 1

    def highlightSquare(self, rank, file, width=SQUARESIZE//15, color=HIGHLIGHT):
        board_x = (self.width - self.board_size) // 2
        board_y = (self.height - self.board_size) // 2

        screen_file = file - 1
        screen_rank = 8 - rank

        rect = pygame.Rect(
            board_x + screen_file * self.square_size,
            board_y + screen_rank * self.square_size,
            self.square_size,
            self.square_size,
        )

        pygame.draw.rect(
            self.screen,
            color,
            rect,
            width
            
        )

    def displayCheckmate(self):
        bRank, bFile = self.game.bitboardToSquare(self.game.black_kings)
        wRank, wFile = self.game.bitboardToSquare(self.game.white_kings)

        if self.game.white_to_move:
            self.highlightSquare(wRank, wFile, self.square_size, (200, 80, 80))
            self.highlightSquare(bRank, bFile, self.square_size, (80, 200, 80))

        else:
            self.highlightSquare(bRank, bFile, self.square_size, (200, 80, 80))
            self.highlightSquare(wRank, wFile, self.square_size, (80, 200, 80))

    def displayDraw(self):
        bRank, bFile = self.game.bitboardToSquare(game_state.black_kings)
        wRank, wFile = self.game.bitboardToSquare(game_state.white_kings)

        self.highlightSquare(wRank, wFile, self.square_size, (140, 140, 140))
        self.highlightSquare(bRank, bFile, self.square_size, (140, 140, 140))

    def drawText(self, text, x, y, color=(255, 255, 255)):
        surface = self.font.render(str(text), True, color)
        self.screen.blit(surface, (x, y))

    def drawPieces(self):
        board_x = (self.width  - self.board_size) // 2
        board_y = (self.height - self.board_size) // 2

        for bitboard_name, image in self.piece_images.items():
            bitboard = getattr(self.game, bitboard_name)

            while bitboard:
                piece_bit = bitboard & -bitboard
                square = piece_bit.bit_length() - 1

                screen_file = square % 8
                chess_rank = square // 8
                screen_rank = 7 - chess_rank

                x = (
                    board_x
                    + screen_file * self.square_size
                    + self.padding
                )

                y = (
                    board_y
                    + screen_rank * self.square_size
                    + self.padding
                )

                self.screen.blit(image, (x, y))

                bitboard &= bitboard - 1

    def mouseToSquare(self, mouse_x, mouse_y):
        board_x = (self.width - self.board_size) // 2
        board_y = (self.height - self.board_size) // 2

        relative_x = mouse_x - board_x
        relative_y = mouse_y - board_y

        if not (0 <= relative_x < self.board_size):
            return None

        if not (0 <= relative_y < self.board_size):
            return None

        file = relative_x // self.square_size + 1
        rank = 8 - relative_y // self.square_size

        return rank, file

    def evalBar(self, eval):
        board_x = (self.width - self.board_size) // 2
        board_y = (self.height   - self.board_size) // 2
    
        padding = self.square_size//3
        border_radius = self.square_size //20
        width = self.square_size//6
        black_percent = 1 - (1.0 / (1.0 + math.exp(-eval / 225.0)))
    
        border = pygame.Rect(
            board_x - padding - border_radius,
            board_y - border_radius,
            width + border_radius * 2,
            self.square_size * 8 + border_radius * 2,
        )
    
        back = pygame.Rect(
            board_x - padding,
            board_y,
            width,
            self.square_size * 8,
        )
        rect = pygame.Rect(
            board_x - padding,
            board_y,
            width,
            min(self.board_size * black_percent, self.board_size - border_radius)
        )
    
        pygame.draw.rect(self.screen, self.highlight, border)
        pygame.draw.rect(self.screen, self.light, back)
        pygame.draw.rect(self.screen, self.dark, rect)
        sign = "+" if eval > 0 else ""
        self.drawText(sign + str(round(eval/100, 2)), board_x - padding - border_radius * 4, board_y + self.board_size + border_radius)

    def run(self):
        # Variables for managing game
        clock = pygame.time.Clock()
        running = True
        playing = True
        selected = False
        selected_rank = None
        selected_file = None
        last_move = None
        moveIndex = -1

        while running:
            # Move Handeling
            checkmate = self.game.isCheckmate()
            draw = self.game.isDraw()

            if not checkmate and not draw:
                # Black plays as bot
                if not self.game.white_to_move:
                    move = self.bot.findMoveToggle(4)
                    self.game.movePiece(move)
                    self.move_sound.play()

                eval = self.bot.evaluator.evaluate(self.game)


            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                # Undo Move
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        playing = False
                        # We need to check if there are any moves for us to undo 
                        if last_move and len(self.game.move_history) >= 1:
                            self.game.undoMove(self.game.move_history[moveIndex])
                            moveIndex -= 1

                    if event.key == pygame.K_RIGHT and not playing:

                        # We need to check if there are any moves for us to undo 
                        if last_move and len(self.game.move_history) >= 1:
                            last_move = self.game.move_history[-1]
                            self.game.movePiece(self.game.move_history[moveIndex])
                            self.move_sound.play()
                            moveIndex += 1

                        # If we are back to our current move we are running again
                        if moveIndex == len(self.game.move_history) - 1:
                            playing = True

                # Moves
                elif event.type == pygame.MOUSEBUTTONDOWN and playing:
                    if event.button != 1:
                        continue
        
                    clicked_square = self.mouseToSquare(*event.pos)
        
                    if clicked_square is None:
                        selected = False
                        continue
        
                    clicked_rank, clicked_file = clicked_square
        
                    # Nothing is currently selected.
                    if not selected:
                        expected_color = "w" if self.game.white_to_move else "b"
        
                        clicked_color = self.game.pieceColor(
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
                        piece = self.game.getPiece(selected_rank, selected_file)
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
        
                        if self.game.moveIsLegal(move):
                            self.game.movePiece(move)
                            self.move_sound.play()
                            moveIndex += 1
                            last_move = move
        
                        selected = False

            # Draw background and board
            self.screen.fill(self.background)
            self.drawBoard()

            # Highlightignn move squares
            if last_move is not None:
                self.highlightSquare(last_move.start_rank, last_move.start_file)
                self.highlightSquare(last_move.end_rank, last_move.end_file)

            # Highlight legal moves
            if selected:
                legalMoves = self.game.getLegalMoves(selected_rank, selected_file)
                self.highlightBitboard(legalMoves)
                self.highlightSquare(selected_rank, selected_file)

            # Display Checkmates and Draws
            if checkmate:
                self.displayCheckmate()

            if draw:
                self.displayDraw()

            # Now draw the rest of the pieces
            self.drawPieces()
            self.evalBar(eval)
            pygame.display.flip()
            clock.tick(60)

        pygame.quit()


        
game = GameState()
bot = Bot(game)
gui = Gui(game, bot)
gui.run()