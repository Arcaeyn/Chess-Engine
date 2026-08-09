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

font = pygame.font.Font(None, 28)
moveSound = pygame.mixer.Sound("sounds/move-self.mp3")
game_state = GameState()
bot = Bot(game_state)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess Engine")
class PieceSprite(pygame.sprite.Sprite)
    def __init__(self, image, rank, file):
        super().__init__()

        self.image = image
        self.rect = self.image.get_rect()

        self.rank = rank
        self.file = file
        self.square_size = square_size

        self.start_position = self.square_center(rank, file)
        self.target_position = self.start_position

        self.animation_time = 0
        self.animation_duration = 200  # milliseconds
        self.animating = False

        self.rect.center = self.start_position



       
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

        # Initialize font, sounds, and screen
        self.font = pygame.font.Font(None, 28)
        self.move_sound = pygame.mixer.Sound("sounds/move-self.mp3")
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
            f"pieces-basic-png/{filename}"
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

    def draw(self):
        self.drawBoard()
        self.drawPieces()

    def animateMove(self, move : Move):
        

        
        
