"""Bitboard chess position and legal move generation.

Square mapping:
    a1 is bit 0, b1 is bit 1, ..., h8 is bit 63.
Ranks and files accepted by the public API are one-indexed (1 through 8).
"""

from __future__ import annotations

from dataclasses import dataclass
from gameLogic.zobrist import (
    PIECE_KEYS,
    SIDE_TO_MOVE_KEY,
    CASTLING_KEYS,
    EN_PASSANT_KEYS,
)


ROOK_DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1))
BISHOP_DIRECTIONS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
QUEEN_DIRECTIONS = ROOK_DIRECTIONS + BISHOP_DIRECTIONS
KNIGHT_DIRECTIONS = (
    (2, 1),
    (2, -1),
    (-2, 1),
    (-2, -1),
    (1, 2),
    (1, -2),
    (-1, 2),
    (-1, -2),
)


@dataclass
class Move:
    start_rank: int
    start_file: int
    end_rank: int
    end_file: int
    promotion: str | None = None
    is_castle: bool = False
    is_en_passant: bool = False

    # Filled by movePiece(). They make undoMove() constant-time and exact.
    moved_piece: str | None = None
    captured_piece: str | None = None
    captured_square: tuple[int, int] | None = None
    previous_state: tuple | None = None
    previous_zobrist_hash: int | None = None



class GameState:
    def __init__(self) -> None:
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
    def white_pieces(self) -> int:
        return (
            self.white_pawns
            | self.white_knights
            | self.white_bishops
            | self.white_rooks
            | self.white_queens
            | self.white_kings
        )

    @property
    def black_pieces(self) -> int:
        return (
            self.black_pawns
            | self.black_knights
            | self.black_bishops
            | self.black_rooks
            | self.black_queens
            | self.black_kings
        )

    @property
    def occupied(self) -> int:
        return self.white_pieces | self.black_pieces

    def resetBoard(self) -> None:
        # White pieces.
        self.white_pawns = 0x000000000000FF00
        self.white_rooks = 0x0000000000000081
        self.white_knights = 0x0000000000000042
        self.white_bishops = 0x0000000000000024
        self.white_queens = 0x0000000000000008
        self.white_kings = 0x0000000000000010

        # Black pieces.
        self.black_pawns = 0x00FF000000000000
        self.black_rooks = 0x8100000000000000
        self.black_knights = 0x4200000000000000
        self.black_bishops = 0x2400000000000000
        self.black_queens = 0x0800000000000000
        self.black_kings = 0x1000000000000000

        self.white_to_move = True
        self.king_in_check = False

        self.white_can_castle_kingside = True
        self.white_can_castle_queenside = True
        self.black_can_castle_kingside = True
        self.black_can_castle_queenside = True

        self.en_passant_square: tuple[int, int] | None = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.move_history: list[Move] = []
        self.position_history: list[tuple] = [self.positionKey()]

        self.zobrist_hash = self.calculateZobristHash()

    def loadFen(self, fen):
        self.resetBoard()

        pieces = True
        piece_map = {
            "p": "black_pawns",
            "r": "black_rooks",
            "n": "black_knights",
            "b": "black_bishops",
            "q": "black_queens",
            "k": "black_kings",
            "P": "white_pawns",
            "R": "white_rooks",
            "N": "white_knights",
            "B": "white_bishops",
            "Q": "white_queens",
            "K": "white_kings",
    }

        # Clear the current position.
        for piece_name in self.piece_names:
            setattr(self, piece_name, 0)

        square_index = 65
        for char in fen:
            if char == " ":
                pieces = False

            if pieces:
                if char.isdigit():
                    square_index -= int(char)

                elif char != "/":
                    square_index -= 1

                    fen_index = 64 - square_index

                    bit_index = (
                        (7 - fen_index // 8) * 8
                        + fen_index % 8
                    )

                    mask = 1 << bit_index

                    piece_name = piece_map[char]
                    bitboard = getattr(self, piece_name)
                    setattr(self, piece_name, bitboard | mask)

            else:
                if char != " ":
                    # Handle whos move it is
                    if char == "w":
                        self.white_to_move = True
                    elif char == "b":
                        self.white_to_move = False

                    # Handle castling
                    if char == "K":
                        self.white_can_castle_kingside = True
                    elif char == "Q":
                        self.white_can_castle_queenside = True

                    elif char == "k":
                        self.black_can_castle_kingside = True

                    elif char == "q":
                        self.black_can_castle_queenside = True

                    # TODO: halfmove clock and enpassant

            self.zobrist_hash = self.calculateZobristHash()


    @staticmethod
    def squareMask(rank: int, file: int) -> int:
        if not (1 <= rank <= 8 and 1 <= file <= 8):
            raise ValueError(f"Square out of bounds: rank={rank}, file={file}")
        return 1 << ((rank - 1) * 8 + (file - 1))

    @staticmethod
    def bitboardToSquare(bitboard: int) -> tuple[int, int]:
        if bitboard == 0 or bitboard & (bitboard - 1):
            raise ValueError("Bitboard must contain exactly one set bit")
        index = bitboard.bit_length() - 1
        return (index // 8) + 1, (index % 8) + 1

    def positionKey(self) -> tuple:
        """Return the rule-relevant position state used for repetition/hashing."""
        return (
            self.white_pawns,
            self.white_knights,
            self.white_bishops,
            self.white_rooks,
            self.white_queens,
            self.white_kings,
            self.black_pawns,
            self.black_knights,
            self.black_bishops,
            self.black_rooks,
            self.black_queens,
            self.black_kings,
            self.white_to_move,
            self.white_can_castle_kingside,
            self.white_can_castle_queenside,
            self.black_can_castle_kingside,
            self.black_can_castle_queenside,
            self.en_passant_square,
        )

    def calculateZobristHash(self):
        zobrist_hash = 0

        # We need to add every piece on the baord to our zobrsit hash
        for piece_name in self.piece_names:
            bitboard = getattr(self, piece_name)

            while bitboard:
                # We isolate the least-sig occupied square
                piece_bit = bitboard &- bitboard

                # Now we convert it to a square index
                square = piece_bit.bit_length() - 1

                # Ok now we have out square so we need to ask it to the combo
                zobrist_hash ^= PIECE_KEYS[piece_name][square]

                # Noq that were done hashing this piece we remove it from our bitboard
                bitboard &= bitboard - 1

        # Ok so supposdely its best to XOR the side key only on blacks moves
        if not self.white_to_move:
            zobrist_hash ^= SIDE_TO_MOVE_KEY

        # also we need to hash the casteling info
        if self.white_can_castle_kingside:
            zobrist_hash ^= CASTLING_KEYS["white_kingside"]

        if self.white_can_castle_queenside:
            zobrist_hash ^= CASTLING_KEYS["white_queenside"]

        if self.black_can_castle_kingside:
            zobrist_hash ^= CASTLING_KEYS["black_kingside"]

        if self.black_can_castle_queenside:
            zobrist_hash ^= CASTLING_KEYS["black_queenside"]

        # and finally we need to hash the current en passant file
        if self.en_passant_square is not None:
            rank, file = self.en_passant_square
            zobrist_hash ^= EN_PASSANT_KEYS[file - 1]

        return zobrist_hash


    def pieceColor(self, rank: int, file: int) -> str | None:
        mask = self.squareMask(rank, file)
        if mask & self.white_pieces:
            return "w"
        if mask & self.black_pieces:
            return "b"
        return None

    def getPiece(self, rank: int, file: int) -> str | None:
        mask = self.squareMask(rank, file)
        for piece_name in self.piece_names:
            if getattr(self, piece_name) & mask:
                return piece_name
        return None

    def isSquareAttacked(self, rank: int, file: int, attacking_color: str) -> bool:
        """Return whether `attacking_color` attacks a square in the current position."""
        if attacking_color not in ("w", "b"):
            raise ValueError("attacking_color must be 'w' or 'b'")

        if attacking_color == "w":
            pawns = self.white_pawns
            knights = self.white_knights
            bishops = self.white_bishops
            rooks = self.white_rooks
            queens = self.white_queens
            kings = self.white_kings

            # White pawns attack upward from one rank below the target.
            source_rank = rank - 1
            if source_rank >= 1:
                if file > 1 and pawns & self.squareMask(source_rank, file - 1):
                    return True
                if file < 8 and pawns & self.squareMask(source_rank, file + 1):
                    return True
        else:
            pawns = self.black_pawns
            knights = self.black_knights
            bishops = self.black_bishops
            rooks = self.black_rooks
            queens = self.black_queens
            kings = self.black_kings

            # Black pawns attack downward from one rank above the target.
            source_rank = rank + 1
            if source_rank <= 8:
                if file > 1 and pawns & self.squareMask(source_rank, file - 1):
                    return True
                if file < 8 and pawns & self.squareMask(source_rank, file + 1):
                    return True

        for rank_delta, file_delta in KNIGHT_DIRECTIONS:
            source_rank = rank + rank_delta
            source_file = file + file_delta
            if 1 <= source_rank <= 8 and 1 <= source_file <= 8:
                if knights & self.squareMask(source_rank, source_file):
                    return True

        for rank_delta, file_delta in QUEEN_DIRECTIONS:
            source_rank = rank + rank_delta
            source_file = file + file_delta
            diagonal = rank_delta != 0 and file_delta != 0
            attackers = (bishops | queens) if diagonal else (rooks | queens)

            while 1 <= source_rank <= 8 and 1 <= source_file <= 8:
                mask = self.squareMask(source_rank, source_file)
                if mask & attackers:
                    return True
                if mask & self.occupied:
                    break
                source_rank += rank_delta
                source_file += file_delta

        for rank_delta, file_delta in QUEEN_DIRECTIONS:
            source_rank = rank + rank_delta
            source_file = file + file_delta
            if 1 <= source_rank <= 8 and 1 <= source_file <= 8:
                if kings & self.squareMask(source_rank, source_file):
                    return True

        return False

    def kingInCheck(self, king_color: str) -> bool:
        king_board = self.white_kings if king_color == "w" else self.black_kings
        if king_board == 0:
            # Missing kings indicate a malformed position. Treat this as check so
            # illegal king-capture lines are never accepted by legal generation.
            return True
        rank, file = self.bitboardToSquare(king_board)
        enemy = "b" if king_color == "w" else "w"
        return self.isSquareAttacked(rank, file, enemy)

    def isCheckmate(self) -> bool:
        color = "w" if self.white_to_move else "b"
        return self.kingInCheck(color) and not self.generateMoves()

    def isStalemate(self) -> bool:
        color = "w" if self.white_to_move else "b"
        return not self.kingInCheck(color) and not self.generateMoves()

    def isFiftyMoveDraw(self) -> bool:
        return self.halfmove_clock >= 100

    def isThreefoldRepetition(self) -> bool:
        current = self.positionKey()
        return self.position_history.count(current) >= 3

    def hasInsufficientMaterial(self) -> bool:
        if self.white_pawns | self.black_pawns | self.white_rooks | self.black_rooks | self.white_queens | self.black_queens:
            return False

        white_knights = self.white_knights.bit_count()
        black_knights = self.black_knights.bit_count()
        white_bishops = self.white_bishops.bit_count()
        black_bishops = self.black_bishops.bit_count()
        total_minors = white_knights + black_knights + white_bishops + black_bishops

        # Restrict automatic draws to unambiguous dead positions. This avoids
        # incorrectly declaring K+BB vs K (which is mating material) a draw.
        return total_minors <= 1

    def isDraw(self) -> bool:
        return (
            self.isStalemate()
            or self.isFiftyMoveDraw()
            or self.isThreefoldRepetition()
            or self.hasInsufficientMaterial()
        )

    def movePiece(self, move: Move) -> bool:
        move.moved_piece = self.getPiece(move.start_rank, move.start_file)
        if move.moved_piece is None:
            return False

        moving_color = "w" if move.moved_piece.startswith("white") else "b"
        if moving_color != ("w" if self.white_to_move else "b"):
            return False
        

        # Save everything undoMove() must restore exactly.
        move.previous_zobrist_hash = self.zobrist_hash
        move.previous_state = (
            self.white_to_move,
            self.white_can_castle_kingside,
            self.white_can_castle_queenside,
            self.black_can_castle_kingside,
            self.black_can_castle_queenside,
            self.en_passant_square,
            self.halfmove_clock,
            self.fullmove_number,
        )

        # Infer special flags when callers construct a plain Move manually.
        if "kings" in move.moved_piece and abs(move.end_file - move.start_file) == 2:
            move.is_castle = True
        if (
            "pawns" in move.moved_piece
            and move.start_file != move.end_file
            and self.getPiece(move.end_rank, move.end_file) is None
            and self.en_passant_square == (move.end_rank, move.end_file)
        ):
            move.is_en_passant = True

        start_mask = self.squareMask(move.start_rank, move.start_file)
        end_mask = self.squareMask(move.end_rank, move.end_file)
        start_square = (move.start_rank - 1) * 8 + (move.start_file - 1)
        end_square = (move.end_rank - 1) * 8 + (move.end_file - 1)

        if move.is_en_passant:
            move.captured_square = (move.start_rank, move.end_file)
        else:
            move.captured_square = (move.end_rank, move.end_file)

        capture_rank, capture_file = move.captured_square
        capture_mask = self.squareMask(capture_rank, capture_file)
        capture_square = (capture_rank - 1) * 8 + (capture_file - 1)
        move.captured_piece = self.getPiece(capture_rank, capture_file)

        # Remove old non-piece state before changing it.
        self.xorCastlingHash()
        self.xorEnPassantHash()

        # Remove the moving piece from its starting square.
        self.zobrist_hash ^= PIECE_KEYS[move.moved_piece][start_square]

        # Remove a captured piece from both the hash and its bitboard.
        if move.captured_piece is not None:
            self.zobrist_hash ^= PIECE_KEYS[move.captured_piece][capture_square]
            captured_board = getattr(self, move.captured_piece)
            setattr(self, move.captured_piece, captured_board & ~capture_mask)

        # Move the piece on the bitboards and add its destination hash key.
        moving_board = getattr(self, move.moved_piece) & ~start_mask
        if move.promotion is not None:
            promoted_board = getattr(self, move.promotion) | end_mask
            setattr(self, move.promotion, promoted_board)
            self.zobrist_hash ^= PIECE_KEYS[move.promotion][end_square]
        else:
            moving_board |= end_mask
            self.zobrist_hash ^= PIECE_KEYS[move.moved_piece][end_square]
        setattr(self, move.moved_piece, moving_board)

        # Castling also moves a rook, so hash both rook squares.
        if move.is_castle:
            rook_name = "white_rooks" if move.moved_piece.startswith("white") else "black_rooks"
            rook_start_file = 8 if move.end_file > move.start_file else 1
            rook_end_file = 6 if move.end_file > move.start_file else 4
            rook_start_square = (move.start_rank - 1) * 8 + (rook_start_file - 1)
            rook_end_square = (move.start_rank - 1) * 8 + (rook_end_file - 1)
            self.zobrist_hash ^= PIECE_KEYS[rook_name][rook_start_square]
            self.zobrist_hash ^= PIECE_KEYS[rook_name][rook_end_square]
            self._move_castling_rook(move, undo=False)

        self._update_castling_rights(move)

        # En passant is available for exactly one opponent move.
        self.en_passant_square = None
        if "pawns" in move.moved_piece and abs(move.end_rank - move.start_rank) == 2:
            middle_rank = (move.start_rank + move.end_rank) // 2
            self.en_passant_square = (middle_rank, move.start_file)

        if "pawns" in move.moved_piece or move.captured_piece is not None:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        if not self.white_to_move:
            self.fullmove_number += 1

        # Add the new non-piece state and flip side-to-move.
        self.xorCastlingHash()
        self.xorEnPassantHash()
        self.zobrist_hash ^= SIDE_TO_MOVE_KEY

        self.move_history.append(move)
        self.white_to_move = not self.white_to_move
        self.position_history.append(self.positionKey())

        return True


    def xorCastlingHash(self):
        if self.white_can_castle_kingside:
            self.zobrist_hash ^= CASTLING_KEYS["white_kingside"]

        if self.white_can_castle_queenside:
            self.zobrist_hash ^= CASTLING_KEYS["white_queenside"]

        if self.black_can_castle_kingside:
            self.zobrist_hash ^= CASTLING_KEYS["black_kingside"]

        if self.black_can_castle_queenside:
            self.zobrist_hash ^= CASTLING_KEYS["black_queenside"]

    def xorEnPassantHash(self):
        if self.en_passant_square is not None:
            rank, file = self.en_passant_square
            self.zobrist_hash ^= EN_PASSANT_KEYS[file - 1]

    def undoMove(self, move: Move | None = None) -> bool:

        if not self.move_history:
            return False
        if move is None:
            move = self.move_history[-1]
       # if self.move_history[-1] is not move:
          #  pass
          #  raise ValueError("undoMove must undo the most recently made move")
        if move.moved_piece is None or move.previous_state is None:
            raise ValueError("Move does not contain undo state")

        start_mask = self.squareMask(move.start_rank, move.start_file)
        end_mask = self.squareMask(move.end_rank, move.end_file)

        if move.is_castle:
            self._move_castling_rook(move, undo=True)

        if move.promotion:
            promoted_board = getattr(self, move.promotion) & ~end_mask
            setattr(self, move.promotion, promoted_board)
            original_board = getattr(self, move.moved_piece) | start_mask
            setattr(self, move.moved_piece, original_board)
        else:
            moving_board = getattr(self, move.moved_piece)
            moving_board &= ~end_mask
            moving_board |= start_mask
            setattr(self, move.moved_piece, moving_board)

        if move.captured_piece is not None and move.captured_square is not None:
            capture_rank, capture_file = move.captured_square
            capture_mask = self.squareMask(capture_rank, capture_file)
            captured_board = getattr(self, move.captured_piece) | capture_mask
            setattr(self, move.captured_piece, captured_board)

        self.move_history.pop()
        if len(self.position_history) > 1:
            self.position_history.pop()

        (
            self.white_to_move,
            self.white_can_castle_kingside,
            self.white_can_castle_queenside,
            self.black_can_castle_kingside,
            self.black_can_castle_queenside,
            self.en_passant_square,
            self.halfmove_clock,
            self.fullmove_number,
        ) = move.previous_state

        self.zobrist_hash = move.previous_zobrist_hash
        
        return True

    def _move_castling_rook(self, move: Move, undo: bool) -> None:
        color_prefix = "white" if move.moved_piece and move.moved_piece.startswith("white") else "black"
        rook_name = f"{color_prefix}_rooks"
        rank = move.start_rank

        if move.end_file > move.start_file:  # kingside
            rook_start_file, rook_end_file = 8, 6
        else:  # queenside
            rook_start_file, rook_end_file = 1, 4

        if undo:
            source_file, destination_file = rook_end_file, rook_start_file
        else:
            source_file, destination_file = rook_start_file, rook_end_file

        source_mask = self.squareMask(rank, source_file)
        destination_mask = self.squareMask(rank, destination_file)
        rook_board = getattr(self, rook_name)
        rook_board &= ~source_mask
        rook_board |= destination_mask
        setattr(self, rook_name, rook_board)

    def _update_castling_rights(self, move: Move) -> None:
        if move.moved_piece == "white_kings":
            self.white_can_castle_kingside = False
            self.white_can_castle_queenside = False
        elif move.moved_piece == "black_kings":
            self.black_can_castle_kingside = False
            self.black_can_castle_queenside = False
        elif move.moved_piece == "white_rooks":
            if (move.start_rank, move.start_file) == (1, 1):
                self.white_can_castle_queenside = False
            elif (move.start_rank, move.start_file) == (1, 8):
                self.white_can_castle_kingside = False
        elif move.moved_piece == "black_rooks":
            if (move.start_rank, move.start_file) == (8, 1):
                self.black_can_castle_queenside = False
            elif (move.start_rank, move.start_file) == (8, 8):
                self.black_can_castle_kingside = False

        if move.captured_piece == "white_rooks":
            if move.captured_square == (1, 1):
                self.white_can_castle_queenside = False
            elif move.captured_square == (1, 8):
                self.white_can_castle_kingside = False
        elif move.captured_piece == "black_rooks":
            if move.captured_square == (8, 1):
                self.black_can_castle_queenside = False
            elif move.captured_square == (8, 8):
                self.black_can_castle_kingside = False

    def moveIsLegal(self, move: Move) -> bool:
        for legal_move in self.generateMoves():
            if (
                legal_move.start_rank == move.start_rank
                and legal_move.start_file == move.start_file
                and legal_move.end_rank == move.end_rank
                and legal_move.end_file == move.end_file
            ):
                if move.promotion is not None and move.promotion != legal_move.promotion:
                    continue
                # Default an unspecified promotion to a queen for UI callers.
                if move.promotion is None and legal_move.promotion and "queens" not in legal_move.promotion:
                    continue
                move.promotion = legal_move.promotion
                move.is_castle = legal_move.is_castle
                move.is_en_passant = legal_move.is_en_passant
                return True
        return False

    def getPseudoLegalMoves(self, rank: int, file: int) -> int:
        piece_name = self.getPiece(rank, file)
        if piece_name is None:
            return 0
        if "pawns" in piece_name:
            return self.getPawnMoves(rank, file)
        if "knights" in piece_name:
            return self.getKnightMoves(rank, file)
        if "bishops" in piece_name:
            return self.getBishopMoves(rank, file)
        if "rooks" in piece_name:
            return self.getRookMoves(rank, file)
        if "queens" in piece_name:
            return self.getQueenMoves(rank, file)
        if "kings" in piece_name:
            return self.getKingMoves(rank, file)
        return 0

    def getLegalMoves(self, rank: int, file: int) -> int:
        legal = 0
        piece_name = self.getPiece(rank, file)
        if piece_name is None:
            return 0
        moving_color = "w" if piece_name.startswith("white") else "b"

        destinations = self.getPseudoLegalMoves(rank, file)
        while destinations:
            destination = destinations & -destinations
            end_rank, end_file = self.bitboardToSquare(destination)
            promotion = None
            if "pawns" in piece_name and end_rank in (1, 8):
                promotion = f"{'white' if moving_color == 'w' else 'black'}_queens"
            move = self._createMove(rank, file, end_rank, end_file, promotion)
            self.movePiece(move)
            if not self.kingInCheck(moving_color):
                legal |= destination
            self.undoMove(move)
            destinations ^= destination
        return legal

    def getKnightMoves(self, rank: int, file: int) -> int:
        color = self.pieceColor(rank, file)
        friendly = self.white_pieces if color == "w" else self.black_pieces
        moves = 0
        for rank_delta, file_delta in KNIGHT_DIRECTIONS:
            new_rank = rank + rank_delta
            new_file = file + file_delta
            if 1 <= new_rank <= 8 and 1 <= new_file <= 8:
                mask = self.squareMask(new_rank, new_file)
                if not mask & friendly:
                    moves |= mask
        return moves

    def getPawnMoves(self, rank: int, file: int) -> int:
        color = self.pieceColor(rank, file)
        if color is None:
            return 0

        direction = 1 if color == "w" else -1
        start_rank = 2 if color == "w" else 7
        enemy = self.black_pieces if color == "w" else self.white_pieces
        moves = 0

        one_rank = rank + direction
        if 1 <= one_rank <= 8:
            one_mask = self.squareMask(one_rank, file)
            if not one_mask & self.occupied:
                moves |= one_mask
                if rank == start_rank:
                    two_rank = rank + 2 * direction
                    two_mask = self.squareMask(two_rank, file)
                    if not two_mask & self.occupied:
                        moves |= two_mask

            for file_delta in (-1, 1):
                target_file = file + file_delta
                if not 1 <= target_file <= 8:
                    continue
                target_mask = self.squareMask(one_rank, target_file)
                if target_mask & enemy or self.en_passant_square == (one_rank, target_file):
                    moves |= target_mask

        return moves

    def getRookMoves(self, rank: int, file: int) -> int:
        return self._slidingMovesForSquare(rank, file, ROOK_DIRECTIONS)

    def getBishopMoves(self, rank: int, file: int) -> int:
        return self._slidingMovesForSquare(rank, file, BISHOP_DIRECTIONS)

    def getQueenMoves(self, rank: int, file: int) -> int:
        return self._slidingMovesForSquare(rank, file, QUEEN_DIRECTIONS)

    def _slidingMovesForSquare(
        self,
        rank: int,
        file: int,
        directions: tuple[tuple[int, int], ...],
    ) -> int:
        color = self.pieceColor(rank, file)
        friendly = self.white_pieces if color == "w" else self.black_pieces
        enemy = self.black_pieces if color == "w" else self.white_pieces
        return self.slidingMoves(rank, file, friendly, enemy, directions)

    def slidingMoves(
        self,
        rank: int,
        file: int,
        friendly_pieces: int,
        enemy_pieces: int,
        directions: tuple[tuple[int, int], ...],
    ) -> int:
        moves = 0
        for rank_delta, file_delta in directions:
            new_rank = rank + rank_delta
            new_file = file + file_delta
            while 1 <= new_rank <= 8 and 1 <= new_file <= 8:
                mask = self.squareMask(new_rank, new_file)
                if mask & friendly_pieces:
                    break
                moves |= mask
                if mask & enemy_pieces:
                    break
                new_rank += rank_delta
                new_file += file_delta
        return moves

    def getKingMoves(self, rank: int, file: int) -> int:
        color = self.pieceColor(rank, file)
        friendly = self.white_pieces if color == "w" else self.black_pieces
        moves = 0

        for rank_delta, file_delta in QUEEN_DIRECTIONS:
            new_rank = rank + rank_delta
            new_file = file + file_delta
            if 1 <= new_rank <= 8 and 1 <= new_file <= 8:
                mask = self.squareMask(new_rank, new_file)
                if not mask & friendly:
                    moves |= mask

        if self._canCastle(color, kingside=True):
            moves |= self.squareMask(rank, 7)
        if self._canCastle(color, kingside=False):
            moves |= self.squareMask(rank, 3)
        return moves

    def _canCastle(self, color: str | None, kingside: bool) -> bool:
        if color not in ("w", "b"):
            return False

        rank = 1 if color == "w" else 8
        king_name = "white_kings" if color == "w" else "black_kings"
        rook_name = "white_rooks" if color == "w" else "black_rooks"
        enemy = "b" if color == "w" else "w"

        if color == "w":
            has_right = self.white_can_castle_kingside if kingside else self.white_can_castle_queenside
        else:
            has_right = self.black_can_castle_kingside if kingside else self.black_can_castle_queenside
        if not has_right:
            return False

        if not getattr(self, king_name) & self.squareMask(rank, 5):
            return False

        rook_file = 8 if kingside else 1
        if not getattr(self, rook_name) & self.squareMask(rank, rook_file):
            return False

        empty_files = (6, 7) if kingside else (2, 3, 4)
        if any(self.occupied & self.squareMask(rank, file) for file in empty_files):
            return False

        transit_files = (5, 6, 7) if kingside else (5, 4, 3)
        if any(self.isSquareAttacked(rank, file, enemy) for file in transit_files):
            return False

        return True

    def _createMove(
        self,
        start_rank: int,
        start_file: int,
        end_rank: int,
        end_file: int,
        promotion: str | None = None,
    ) -> Move:
        piece_name = self.getPiece(start_rank, start_file)
        is_castle = bool(piece_name and "kings" in piece_name and abs(end_file - start_file) == 2)
        is_en_passant = bool(
            piece_name
            and "pawns" in piece_name
            and start_file != end_file
            and self.getPiece(end_rank, end_file) is None
            and self.en_passant_square == (end_rank, end_file)
        )
        return Move(
            start_rank,
            start_file,
            end_rank,
            end_file,
            promotion=promotion,
            is_castle=is_castle,
            is_en_passant=is_en_passant,
        )

    def generateMovesFromBitboard(self, bitboard: int, move_generator) -> list[Move]:
        moves: list[Move] = []
        while bitboard:
            piece_mask = bitboard & -bitboard
            start_rank, start_file = self.bitboardToSquare(piece_mask)
            piece_name = self.getPiece(start_rank, start_file)
            destinations = move_generator(start_rank, start_file)

            while destinations:
                destination = destinations & -destinations
                end_rank, end_file = self.bitboardToSquare(destination)
                target_piece = self.getPiece(end_rank, end_file)

                # Kings are checked, not captured. Skipping an enemy king square
                # also makes malformed positions fail safely.
                if target_piece is not None and "kings" in target_piece:
                    destinations ^= destination
                    continue

                if piece_name and "pawns" in piece_name and end_rank in (1, 8):
                    prefix = "white" if piece_name.startswith("white") else "black"
                    for promotion_piece in ("queens", "knights", "bishops", "rooks"):
                        moves.append(
                            self._createMove(
                                start_rank,
                                start_file,
                                end_rank,
                                end_file,
                                promotion=f"{prefix}_{promotion_piece}",
                            )
                        )
                else:
                    moves.append(self._createMove(start_rank, start_file, end_rank, end_file))

                destinations ^= destination
            bitboard ^= piece_mask
        return moves

    def generatePseudoMoves(self) -> list[Move]:
        if self.white_to_move:
            return (
                self.generateMovesFromBitboard(self.white_pawns, self.getPawnMoves)
                + self.generateMovesFromBitboard(self.white_knights, self.getKnightMoves)
                + self.generateMovesFromBitboard(self.white_bishops, self.getBishopMoves)
                + self.generateMovesFromBitboard(self.white_rooks, self.getRookMoves)
                + self.generateMovesFromBitboard(self.white_queens, self.getQueenMoves)
                + self.generateMovesFromBitboard(self.white_kings, self.getKingMoves)
            )
        return (
            self.generateMovesFromBitboard(self.black_pawns, self.getPawnMoves)
            + self.generateMovesFromBitboard(self.black_knights, self.getKnightMoves)
            + self.generateMovesFromBitboard(self.black_bishops, self.getBishopMoves)
            + self.generateMovesFromBitboard(self.black_rooks, self.getRookMoves)
            + self.generateMovesFromBitboard(self.black_queens, self.getQueenMoves)
            + self.generateMovesFromBitboard(self.black_kings, self.getKingMoves)
        )

    def generateMoves(self) -> list[Move]:
        legal_moves: list[Move] = []
        moving_color = "w" if self.white_to_move else "b"

        for move in self.generatePseudoMoves():
            self.movePiece(move)
            if not self.kingInCheck(moving_color):
                legal_moves.append(move)
            self.undoMove(move)

        return legal_moves
