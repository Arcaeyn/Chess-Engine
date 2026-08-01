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

        moving_piece_name = self.getPiece(
            move.start_rank,
            move.start_file,
        )

        if moving_piece_name is None:
            return False

        # Remove a captured piece from the destination.
        captured_piece_name = self.getPiece(
            move.end_rank,
            move.end_file,
        )

        if captured_piece_name is not None:
            captured_bitboard = getattr(self, captured_piece_name)
            captured_bitboard &= ~destination_mask
            setattr(self, captured_piece_name, captured_bitboard)

        # Remove the moving piece from its starting square.
        moving_bitboard = getattr(self, moving_piece_name)
        moving_bitboard &= ~selected_mask

        # Place it on the destination square.
        moving_bitboard |= destination_mask
        setattr(self, moving_piece_name, moving_bitboard)

        self.move_history.append(move)
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

        return 0

    def getKnightMoves(self, rank, file, color="w"):
        knight_directions = [
            (2, 1),
            (2, -1),
            (-2, 1),
            (-2, -1),
            (1, 2),
            (1, -2),
            (-1, 2),
            (-1, -2),
        ]

        knight_moves = 0

        for rank_change, file_change in knight_directions:
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

        for rank_change in moves:
            new_rank = rank + rank_change

            if 1 <= new_rank <= 8:
                move_mask = self.squareMask(new_rank, file)
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