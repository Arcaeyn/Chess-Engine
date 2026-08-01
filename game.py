import pygame
from board import Board

pygame.init()


WIDTH = 900
HEIGHT = 800

BOARDSIZE = 700
SQUARESIZE = BOARDSIZE//8
PADDING = SQUARESIZE//15

LIGHT = (232, 239, 255)
DARK = (120, 142, 191)
HIGHLIGHT = (120, 120, 140)

whiteToMove = True
font = pygame.font.Font(None, 28)
peices = Board()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess Engine")


# Loading our assets, the board is drawn by the program so we just need to worry about piece images
def load_piece_image(filename):
    image = pygame.image.load(
        f"pieces-basic-png/{filename}"
    ).convert_alpha()

    piece_size = SQUARESIZE - (PADDING * 2)

    return pygame.transform.smoothscale(
        image,
        (piece_size, piece_size)
    )

PIECE_IMAGES = {
    "white_pawns": load_piece_image("white-pawn.png"),
    "white_rooks": load_piece_image("white-rook.png"),
    "white_knights": load_piece_image("white-knight.png"),
    "white_bishops": load_piece_image("white-bishop.png"),
    "white_queens": load_piece_image("white-queen.png"),
    "white_kings": load_piece_image("white-king.png"),

    "black_pawns": load_piece_image("black-pawn.png"),
    "black_rooks": load_piece_image("black-rook.png"),
    "black_knights": load_piece_image("black-knight.png"),
    "black_bishops": load_piece_image("black-bishop.png"),
    "black_queens": load_piece_image("black-queen.png"),
    "black_kings": load_piece_image("black-king.png"),
}


# Useful Functions For Drawing Our Board
def drawBoard():
    for file in range(8):
        labelnums = font.render(str(8 - file), True, DARK if file%2 == 0  else LIGHT)
        labelletters = font.render("abcdefgh"[file], True, LIGHT if file%2 == 0  else DARK)
        
        for rank in range(8):
            color = LIGHT if (rank + file)%2 == 0 else DARK
            

            rect = pygame.Rect(
                file * SQUARESIZE + (WIDTH - BOARDSIZE)//2,
                rank * SQUARESIZE + (HEIGHT - BOARDSIZE)//2,
                SQUARESIZE,
                SQUARESIZE
            )

            pygame.draw.rect(screen, color, rect)
        screen.blit(labelnums, ((WIDTH - BOARDSIZE)//2 + PADDING,  file * SQUARESIZE + (HEIGHT - BOARDSIZE)//2 + PADDING))
        screen.blit(labelletters, ((WIDTH - BOARDSIZE)//2 - PADDING * 3 + (file + 1) * SQUARESIZE,  (HEIGHT - BOARDSIZE)//2 + BOARDSIZE - PADDING * 5))

def create_circle_surface(radius, color):
    # 1 & 2: Create a square canvas with per-pixel alpha (transparency)
    diameter = radius * 2
    circle_surface = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
    
    # 3: Draw a filled circle in the exact center of this new surface
    pygame.draw.circle(circle_surface, color, (radius, radius), radius)
    
    return circle_surface

def highlightBitBoard(bitboard):
    board_x = (WIDTH - BOARDSIZE) // 2
    board_y = (HEIGHT - BOARDSIZE) // 2

    # Transparent yellow highlight
    highlight = create_circle_surface(SQUARESIZE//6, (80, 80, 80))

    while bitboard:
        # Find the lowest occupied bit
        square = (bitboard & -bitboard).bit_length() - 1

        file = square % 8
        chess_rank = square // 8
        screen_rank = 7 - chess_rank

        x = board_x + file * SQUARESIZE + SQUARESIZE//3
        y = board_y + screen_rank * SQUARESIZE + SQUARESIZE//3

        screen.blit(highlight, (x, y), special_flags=pygame.BLEND_RGB_SUB)

        # Remove the bit we just highlighted
        bitboard &= bitboard - 1

def highlightSquare(file, rank):

    rect = pygame.Rect(
                    (rank - 1) * SQUARESIZE + (WIDTH - BOARDSIZE)//2,
                    (8 - file) * SQUARESIZE + (HEIGHT - BOARDSIZE)//2,
                    SQUARESIZE,
                    SQUARESIZE
                )
    pygame.draw.rect(screen, (200, 100, 100), rect)

def drawPieces():
    board_x = (WIDTH - BOARDSIZE) // 2
    board_y = (HEIGHT - BOARDSIZE) // 2

    for bitboard_name, image in PIECE_IMAGES.items():
        bitboard = getattr(peices, bitboard_name)

        while bitboard:
            # Isolate the lowest occupied bit
            piece_bit = bitboard & -bitboard

            # Convert that bit to a square from 0 to 63
            square = piece_bit.bit_length() - 1

            # Convert bitboard square to file and rank
            file = square % 8
            chess_rank = square // 8

            # Pygame starts at the top, so flip the rank
            screen_rank = 7 - chess_rank

            x = board_x + file * SQUARESIZE + PADDING
            y = board_y + screen_rank * SQUARESIZE + PADDING

            screen.blit(image, (x, y))

            # Remove the piece we just drew
            bitboard &= bitboard - 1

# Converts a mouse position to a file and rank on the chess board
def mouseToSquare(mousex, mousey):
    boardx = (WIDTH-BOARDSIZE)//2
    boardy = (HEIGHT - BOARDSIZE)//2

    relx = boardx - mousex
    rely = boardy - mousey

    rank = 9 - rely//SQUARESIZE * - 1
    file = relx//SQUARESIZE * -1

    if rank > 0 and rank < 9 and file > 0 and file < 9:
        return (rank, file)

    return False
    

# Game Loop and Such
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess Engine")

clock = pygame.time.Clock()

# Variables to handle click/drag/game loop
running = True
placed = False
selected = False

drawPieces()
while running:
    # Handle events
    for event in pygame.event.get():

        # Window Logic
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            peices.resetBoard()

        # When a mouse button is first pressed
        if event.type == pygame.MOUSEBUTTONDOWN:

            # We need to know whether we already have a square curr selected
            # If it is the same square than we need to deselected
            if selected:
                dest_x, dest_y = event.pos
                destRank, destFile = mouseToSquare(dest_x, dest_y)

                # If its a differnet square than we move to a diff square
                if destRank != selRank or destFile != selFile:
                    placed = True

                selected = False

            # If nothing is selceted select the curr square
            else:
                sel_x, sel_y = event.pos
                selRank, selFile = mouseToSquare(sel_x, sel_y)
                selected = True

        # When a mouse button is released
        if event.type == pygame.MOUSEBUTTONUP and selected:
            dest_x, dest_y = event.pos
            destRank, destFile = mouseToSquare(dest_x, dest_y)

            # we dont want to release on the same square we selected and have some odd shit happen
            # This gives us drag and drop functinoality
            # TODO: if the selected piece has been selected usign a mousedown and the mouse has not detcted a mouse up
            # But its position has changed to a diff square than we know that the user is trying to drag and drop the piece
            # This means we can temproarily snap the piece image to the mouse until we detectd a mouse up that lands on a diff square
            if selRank != destRank or selFile != destFile:
                placed = True
                selected = False

    mouse_x, mouse_y = pygame.mouse.get_pos()

    # Draw everything
    screen.fill((30, 30, 40))
    drawBoard()

    # Logic to Handle Moving Pieces
    # This just highlights the selected Piece, it unhilights once a turn changes maybe I need to fix this
    if selected:
        highlightBitBoard(peices.getPseduoLegalMoves(selRank, selFile))
        highlightSquare(selRank, selFile)

    # Check if a move is legal before allowing it
    legalMove = False
    if placed:
        legalMove = peices.moveIsLegal(selRank, selFile, destRank, destFile)

    # This will handle moving/placing a white piece
    if placed and whiteToMove and peices.pieceColor(selRank, selFile) == "w" and legalMove:
        placed = False
        selected = False
        whiteToMove = False
        peices.movePiece(selRank, selFile, destRank, destFile)
        highlightSquare(selRank, selFile)
        highlightSquare(destRank, destFile)

    # And this handles black pieces being moved
    elif placed and not whiteToMove and peices.pieceColor(selRank, selFile) == "b" and legalMove:
        placed = False
        selected = False
        whiteToMove = True
        peices.movePiece(selRank, selFile, destRank, destFile)
        highlightSquare(selRank, selFile)
        highlightSquare(destRank, destFile)

    # Otherwise nothing has been placed
    else:
        placed = False

    # Now that all highlighting and legal moves are drawn we can draw pieces and display
    drawPieces()
    # Show what was drawn
    pygame.display.flip()

    # Limit the program to 60 frames per second
    clock.tick(60)

pygame.quit()


