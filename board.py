from dataclasses import dataclass


# Valid sliding-piece directions
ROOK_DIRECTIONS = [
    (1, 0),
    (-1, 0),
    (0, 1),
    (0, -1),
]

BISHOP_DIRECTIONS = [
    (1, 1),
    (1, -1),
    (-1, 1),
    (-1, -1),
]

KNIGHT_DIRECTIONS = [
            (2, 1),
            (2, -1),
            (-2, 1),
            (-2, -1),
            (1, 2),
            (1, -2),
            (-1, 2),
            (-1, -2),
        ]

QUEEN_DIRECTIONS = ROOK_DIRECTIONS + BISHOP_DIRECTIONS


@dataclass
class Move:
    start_rank: int
    start_file: int
    end_rank: int
    end_file: int
    promotion: str | None = None
    is_castle: bool = False
    is_en_passant: bool = False

    moved_piece: str | None = None
    captured_peice: str | None = None


class GameState:
    def __init__(self):
        self.piece_names = [
            "white_pawns",
            "black_pawns",
            "white_rooks",
            "black_rooks",
            "white_knights",
            "black_knights",
            "white_bishops",
            "black_bishops",
            "white_queens",
            "black_queens",
            "white_kings",
            "black_kings",
        ]

        self.resetBoard()

    @property
    def white_pieces(self):
        return (
            self.white_rooks
            | self.white_knights
            | self.white_bishops
            | self.white_queens
            | self.white_kings
            | self.white_pawns
        )

    @property
    def black_pieces(self):
        return (
            self.black_rooks
            | self.black_knights
            | self.black_bishops
            | self.black_queens
            | self.black_kings
            | self.black_pawns
        )

    @property
    def occupied(self):
        return self.white_pieces | self.black_pieces

    def resetBoard(self):
        # White pieces
        self.white_pawns = 0x000000000000FF00
        self.white_rooks = 0x0000000000000081
        self.white_knights = 0x0000000000000042
        self.white_bishops = 0x0000000000000024
        self.white_queens = 0x0000000000000008
        self.white_kings = 0x0000000000000010

        # Black pieces
        self.black_pawns = 0x00FF000000000000
        self.black_rooks = 0x8100000000000000
        self.black_knights = 0x4200000000000000
        self.black_bishops = 0x2400000000000000
        self.black_queens = 0x0800000000000000
        self.black_kings = 0x1000000000000000

        # Game state
        self.white_to_move = True
        self.king_in_check = False

        self.white_can_castle_kingside = True
        self.white_can_castle_queenside = True
        self.black_can_castle_kingside = True
        self.black_can_castle_queenside = True

        self.en_passant_square = None
        self.move_history = []

    def squareMask(self, rank, file):
        return 1 << ((rank - 1) * 8 + (file - 1))

    def isSquareAttacked(self, rank, file, attacking_color):
        square_mask = self.squareMask(rank, file)
        if attacking_color == "w":

            # Check for pawn attacks
            if ((square_mask >> 9) & self.white_pawns or (square_mask >> 7) & self.white_pawns) and rank > 1:
                return True
            
            # Check for knight attacks
            for rank_change, file_change in KNIGHT_DIRECTIONS:
                new_rank = rank + rank_change
                new_file = file + file_change

                if (1 <= new_rank <= 8 and 1 <= new_file <= 8):
                    knight_mask = self.squareMask(new_rank, new_file)
                    if knight_mask and self.white_knights:
                        return True
                    
            # Check for sliding attacks
            for rank_change, file_change in QUEEN_DIRECTIONS:
                new_rank = rank + rank_change
                new_file = file + file_change
                while 1 <= new_rank <= 8 and 1 <= new_file <= 8:
                    square_mask = self.squareMask(new_rank, new_file)
                    
                    # Check for Bishop
                    if square_mask and self.white_bishops:
                        return True
                    
                    # Check for Queens
                    if square_mask and self.white_queens:
                        return True
                    
                    # Check for Bishop
                    if square_mask and self.white_bishops:
                        return True
                    
                    # Check for Rooks
                    if square_mask and self.white_rooks:
                        return True
                    
                    new_rank += rank_change
                    new_file += file_change

            return False
      




    def pieceColor(self, rank, file):
        piece_mask = self.squareMask(rank, file)

        if piece_mask & self.white_pieces:
            return "w"

        if piece_mask & self.black_pieces:
            return "b"

        return None

    def getPiece(self, rank, file):
        piece_mask = self.squareMask(rank, file)

        for piece_name in self.piece_names:
            piece_bitboard = getattr(self, piece_name)

            if piece_bitboard & piece_mask:
                return piece_name

        return None

    def movePiece(self, move):
        selected_mask = self.squareMask(
            move.start_rank,
            move.start_file,
        )

        destination_mask = self.squareMask(
            move.end_rank,
            move.end_file,
        )

        move.moved_piece = self.getPiece(
            move.start_rank,
            move.start_file,
        )


        if move.moved_piece is None:
            return False

        # Remove a captured piece from the destination.
        move.captured_piece = self.getPiece(
            move.end_rank,
            move.end_file,
        )

        if move.captured_piece is not None:
            captured_bitboard = getattr(self, move.captured_piece)
            captured_bitboard &= ~destination_mask
            setattr(self, move.captured_piece, captured_bitboard)

        # Remove the moving piece from its starting square.
        moving_bitboard = getattr(self, move.moved_piece)
        moving_bitboard &= ~selected_mask

        # Place it on the destination square.
        moving_bitboard |= destination_mask
        setattr(self, move.moved_piece, moving_bitboard)

        self.move_history.append(move)
        self.white_to_move = not self.white_to_move

        return True

    def undoMove(self, move):
        selected_mask = self.squareMask(
            move.start_rank,
            move.start_file,
        )

        destination_mask = self.squareMask(
            move.end_rank,
            move.end_file,
        )
        
        # Replace any captured piece
        if move.captured_piece:
            captured_bitboard = getattr(self, move.captured_piece)
            captured_bitboard |= destination_mask
            setattr(self, move.captured_piece, captured_bitboard)

        # Remove the movied piece from the destination square and then place it back onto the selected square
        moving_bitboard = getattr(self, move.moved_piece)
        moving_bitboard &= ~destination_mask
        moving_bitboard |= selected_mask
        setattr(self, move.moved_piece, moving_bitboard)

        # Update state
        # Remove this move from the history as we are undoing it, also update whose move 
        self.move_history.pop(-1)
        self.white_to_move = not self.white_to_move

        return True

    def moveIsLegal(self, move):
        legal_moves = self.getPseudoLegalMoves(
            move.start_rank,
            move.start_file,
        )

        destination_mask = self.squareMask(
            move.end_rank,
            move.end_file,
        )

        return bool(legal_moves & destination_mask)

    def getPseudoLegalMoves(self, rank, file):
        piece_name = self.getPiece(rank, file)

        if piece_name is None:
            return 0

        color = piece_name[0]

        if "bishop" in piece_name:
            return self.getBishopMoves(rank, file, color)

        if "knight" in piece_name:
            return self.getKnightMoves(rank, file, color)

        if "rook" in piece_name:
            return self.getRookMoves(rank, file, color)

        if "queen" in piece_name:
            return self.getQueenMoves(rank, file, color)

        if "pawn" in piece_name:
            return self.getPawnMoves(rank, file, color)
        
        if "king" in piece_name:
            return self.getKingMoves(rank, file, color)

        return 0

    def getKnightMoves(self, rank, file, color="w"):
        knight_moves = 0

        for rank_change, file_change in KNIGHT_DIRECTIONS:
            new_rank = rank + rank_change
            new_file = file + file_change

            if not (1 <= new_rank <= 8 and 1 <= new_file <= 8):
                continue

            if self.pieceColor(new_rank, new_file) == color:
                continue

            move_mask = self.squareMask(new_rank, new_file)
            knight_moves |= move_mask

        return knight_moves

    def getPawnMoves(self, rank, file, color="w"):
        pawn_moves = 0

        if color == "b":
            moves = [-1, -2] if rank == 7 else [-1]
        else:
            moves = [1, 2] if rank == 2 else [1]

        # Attacking - first define the square in front of us
        ahead_mask = self.squareMask(rank + moves[0], file)

        # If we arent on the first or last file our mask must be both diagnols
        if file > 1 and file < 8:
            diag_right = ahead_mask << 1
            diag_left = ahead_mask >> 1

        # Otherwise we only have one valid diag
        elif file == 1:
            diag_right = ahead_mask << 1
            diag_left = 0

        else:
            diag_left = ahead_mask >> 1
            diag_right = 0

        # Now we create our attack mask and if it overlaops with an enemy peice we can add that to out valid pawn moves
        attack_mask = 0 | diag_left | diag_right
        if color == "w":
            pawn_moves |= (attack_mask & self.black_pieces)

        else:
            pawn_moves |= (attack_mask & self.white_pieces)


        # For stepping forawrd a rank (or two if we are on startin square)
        for rank_change in moves:
            new_rank = rank + rank_change
            if 1 <= new_rank <= 8:
                move_mask = self.squareMask(new_rank, file)
                if not move_mask & self.occupied:
                    pawn_moves |= move_mask

        return pawn_moves

    def getRookMoves(self, rank, file, color="w"):
        if color == "w":
            friendly_pieces = self.white_pieces
            enemy_pieces = self.black_pieces
        else:
            friendly_pieces = self.black_pieces
            enemy_pieces = self.white_pieces

        return self.slidingMoves(
            rank,
            file,
            friendly_pieces,
            enemy_pieces,
            ROOK_DIRECTIONS,
        )

    def getKingMoves(self, rank, file, color="w"):
        king_moves = 0

        # This will handle king moving to ajacent squares
        for rank_change, file_change in QUEEN_DIRECTIONS:
            if rank + rank_change >= 1 and rank + rank_change <= 8 and file + file_change >= 1 and file + file_change <= 8:
                move_mask = self.squareMask(rank + rank_change, file + file_change)
                if color == "w":
                    if not move_mask & self.white_pieces:
                        king_moves |= move_mask

                else:
                    if not move_mask & self.black_pieces:
                        king_moves |= move_mask
        return king_moves
        # We still need to do castling
        
    def getBishopMoves(self, rank, file, color="w"):
        if color == "w":
            friendly_pieces = self.white_pieces
            enemy_pieces = self.black_pieces
        else:
            friendly_pieces = self.black_pieces
            enemy_pieces = self.white_pieces

        return self.slidingMoves(
            rank,
            file,
            friendly_pieces,
            enemy_pieces,
            BISHOP_DIRECTIONS,
        )

    def getQueenMoves(self, rank, file, color="w"):
        if color == "w":
            friendly_pieces = self.white_pieces
            enemy_pieces = self.black_pieces
        else:
            friendly_pieces = self.black_pieces
            enemy_pieces = self.white_pieces

        return self.slidingMoves(
            rank,
            file,
            friendly_pieces,
            enemy_pieces,
            QUEEN_DIRECTIONS,
        )

    def slidingMoves(
        self,
        rank,
        file,
        friendly_pieces,
        enemy_pieces,
        directions,
    ):
        moves = 0

        for rank_change, file_change in directions:
            new_rank = rank + rank_change
            new_file = file + file_change

            while 1 <= new_rank <= 8 and 1 <= new_file <= 8:
                move_mask = self.squareMask(new_rank, new_file)

                # Friendly pieces block movement.
                if friendly_pieces & move_mask:
                    break

                # Empty and enemy squares are possible destinations.
                moves |= move_mask

                # Enemy pieces can be captured, but not passed through.
                if enemy_pieces & move_mask:
                    break

                new_rank += rank_change
                new_file += file_change

        return moves