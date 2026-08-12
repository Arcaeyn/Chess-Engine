"""Optimized bitboard chess position and legal move generation.

Square mapping
--------------
Internally the engine uses zero-indexed square numbers:
    a1 = 0, b1 = 1, ..., h8 = 63.

The public API still accepts/returns one-indexed ``(rank, file)`` pairs so the
rest of the project can keep using the same interface it used before.

Performance design
------------------
The search hot path avoids the main sources of Python overhead from the older
implementation:

* Piece lookup uses a 64-entry mailbox instead of scanning 12 bitboards.
* White/black/all occupancy bitboards are cached and updated incrementally.
* Knight, king, pawn attacks, directional rays, and BETWEEN masks are
  precomputed once at import time.
* Sliding attacks use precomputed rays plus the nearest blocker instead of
  walking square-by-square in Python.
* ``generateMoves()`` generates legal moves directly from check/pin masks.
  It no longer makes and undoes every pseudo-legal move just to test legality.
* En-passant is the only ordinary non-king move that receives a tiny occupancy
  simulation, because removing the captured pawn can reveal a rook/bishop line.
* Repetition history stores the incremental Zobrist hash rather than allocating
  a large position tuple after every search move.

The code intentionally keeps the old public helper methods (``getPawnMoves``,
``getLegalMoves``, etc.) for compatibility, but the search path uses the faster
square-indexed helpers below.
"""

from __future__ import annotations

from dataclasses import dataclass
from gameLogic.zobrist import (
    PIECE_KEYS,
    SIDE_TO_MOVE_KEY,
    CASTLING_KEYS,
    EN_PASSANT_KEYS,
)


# ---------------------------------------------------------------------------
# Board constants and precomputed attack data
# ---------------------------------------------------------------------------

FULL_BOARD = (1 << 64) - 1
SQUARE_MASKS = tuple(1 << square for square in range(64))

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

# A direction's square-number delta also tells us which end of a ray contains
# the nearest blocker. Positive deltas move toward more-significant bits;
# negative deltas move toward less-significant bits.
DIRECTION_DELTAS = {
    (1, 0): 8,    # north
    (-1, 0): -8,  # south
    (0, 1): 1,    # east
    (0, -1): -1,  # west
    (1, 1): 9,    # north-east
    (1, -1): 7,   # north-west
    (-1, 1): -7,  # south-east
    (-1, -1): -9, # south-west
}


def _coords_to_index(rank_index: int, file_index: int) -> int:
    """Convert zero-indexed rank/file coordinates to a square number."""
    return (rank_index << 3) | file_index


def _index_to_public(square: int) -> tuple[int, int]:
    """Convert a square number to one-indexed public rank/file coordinates."""
    return (square >> 3) + 1, (square & 7) + 1


def _public_to_index(rank: int, file: int) -> int:
    """Convert one-indexed public rank/file coordinates to a square number."""
    if not (1 <= rank <= 8 and 1 <= file <= 8):
        raise ValueError(f"Square out of bounds: rank={rank}, file={file}")
    return ((rank - 1) << 3) | (file - 1)


def _lsb_square(bitboard: int) -> int:
    """Return the square number of the least-significant set bit."""
    return (bitboard & -bitboard).bit_length() - 1


def _msb_square(bitboard: int) -> int:
    """Return the square number of the most-significant set bit."""
    return bitboard.bit_length() - 1


def _build_jump_attacks(directions: tuple[tuple[int, int], ...]) -> tuple[int, ...]:
    """Build attack masks for pieces whose moves do not depend on blockers."""
    table: list[int] = [0] * 64
    for square in range(64):
        rank = square >> 3
        file = square & 7
        attacks = 0
        for rank_delta, file_delta in directions:
            target_rank = rank + rank_delta
            target_file = file + file_delta
            if 0 <= target_rank < 8 and 0 <= target_file < 8:
                attacks |= SQUARE_MASKS[_coords_to_index(target_rank, target_file)]
        table[square] = attacks
    return tuple(table)


def _build_pawn_attacks(color: str) -> tuple[int, ...]:
    """Build pawn capture masks for one color."""
    table: list[int] = [0] * 64
    direction = 1 if color == "w" else -1
    for square in range(64):
        rank = square >> 3
        file = square & 7
        target_rank = rank + direction
        attacks = 0
        if 0 <= target_rank < 8:
            if file > 0:
                attacks |= SQUARE_MASKS[_coords_to_index(target_rank, file - 1)]
            if file < 7:
                attacks |= SQUARE_MASKS[_coords_to_index(target_rank, file + 1)]
        table[square] = attacks
    return tuple(table)


def _build_rays() -> dict[tuple[int, int], tuple[int, ...]]:
    """Precompute every unobstructed directional ray from every square."""
    rays: dict[tuple[int, int], tuple[int, ...]] = {}
    for direction in QUEEN_DIRECTIONS:
        rank_delta, file_delta = direction
        table: list[int] = [0] * 64
        for square in range(64):
            rank = square >> 3
            file = square & 7
            ray = 0
            rank += rank_delta
            file += file_delta
            while 0 <= rank < 8 and 0 <= file < 8:
                ray |= SQUARE_MASKS[_coords_to_index(rank, file)]
                rank += rank_delta
                file += file_delta
            table[square] = ray
        rays[direction] = tuple(table)
    return rays


def _build_between() -> tuple[tuple[int, ...], ...]:
    """Build masks of squares strictly between two aligned squares.

    Non-aligned square pairs receive a zero mask. This lets single-check
    evasion reduce to ``BETWEEN[king][checker] | checker_bit`` for sliders.
    """
    table: list[list[int]] = [[0] * 64 for _ in range(64)]

    for start in range(64):
        start_rank = start >> 3
        start_file = start & 7
        for end in range(64):
            if start == end:
                continue

            end_rank = end >> 3
            end_file = end & 7
            rank_diff = end_rank - start_rank
            file_diff = end_file - start_file

            if rank_diff == 0:
                rank_step = 0
                file_step = 1 if file_diff > 0 else -1
            elif file_diff == 0:
                rank_step = 1 if rank_diff > 0 else -1
                file_step = 0
            elif abs(rank_diff) == abs(file_diff):
                rank_step = 1 if rank_diff > 0 else -1
                file_step = 1 if file_diff > 0 else -1
            else:
                continue

            rank = start_rank + rank_step
            file = start_file + file_step
            between = 0
            while (rank, file) != (end_rank, end_file):
                between |= SQUARE_MASKS[_coords_to_index(rank, file)]
                rank += rank_step
                file += file_step
            table[start][end] = between

    return tuple(tuple(row) for row in table)


KNIGHT_ATTACKS = _build_jump_attacks(KNIGHT_DIRECTIONS)
KING_ATTACKS = _build_jump_attacks(QUEEN_DIRECTIONS)
WHITE_PAWN_ATTACKS = _build_pawn_attacks("w")
BLACK_PAWN_ATTACKS = _build_pawn_attacks("b")
RAYS = _build_rays()
BETWEEN = _build_between()


@dataclass(slots=True)
class Move:
    """A chess move.

    Rank/file fields remain one-indexed for compatibility with the GUI and the
    rest of the project. Search-generated moves also carry the moving/captured
    piece names so move application never needs a 12-bitboard scan.
    """

    start_rank: int
    start_file: int
    end_rank: int
    end_file: int
    promotion: str | None = None
    is_castle: bool = False
    is_en_passant: bool = False

    # Filled by move generation / movePiece(). They make undoMove() constant-time.
    moved_piece: str | None = None
    captured_piece: str | None = None
    captured_square: tuple[int, int] | None = None
    previous_state: tuple | None = None
    previous_zobrist_hash: int | None = None


class GameState:
    """Bitboard chess position with optimized legal move generation."""

    PIECE_NAMES = (
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
    )

    def __init__(self) -> None:
        # Keep an instance attribute because older code may access piece_names.
        self.piece_names = list(self.PIECE_NAMES)
        self.resetBoard()

    # ------------------------------------------------------------------
    # Cached occupancy
    # ------------------------------------------------------------------

    @property
    def white_pieces(self) -> int:
        """All white pieces. Kept as a property for old callers, now O(1)."""
        return self.white_occupied

    @property
    def black_pieces(self) -> int:
        """All black pieces. Kept as a property for old callers, now O(1)."""
        return self.black_occupied

    @property
    def occupied(self) -> int:
        """All occupied squares. Kept as a property for old callers, now O(1)."""
        return self.all_occupied

    def _rebuild_fast_state(self) -> None:
        """Rebuild mailbox and cached occupancies after bulk position loading.

        Search moves update these structures incrementally; this helper is only
        needed after reset/FEN loading where rebuilding once is simpler.
        """
        self.white_occupied = (
            self.white_pawns
            | self.white_knights
            | self.white_bishops
            | self.white_rooks
            | self.white_queens
            | self.white_kings
        )
        self.black_occupied = (
            self.black_pawns
            | self.black_knights
            | self.black_bishops
            | self.black_rooks
            | self.black_queens
            | self.black_kings
        )
        self.all_occupied = self.white_occupied | self.black_occupied

        # Mailbox gives O(1) piece lookup. Bitboards remain the authoritative
        # representation for move generation.
        self.board: list[str | None] = [None] * 64
        for piece_name in self.PIECE_NAMES:
            bitboard = getattr(self, piece_name)
            while bitboard:
                piece_bit = bitboard & -bitboard
                square = piece_bit.bit_length() - 1
                self.board[square] = piece_name
                bitboard ^= piece_bit

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
        self.king_in_check = False  # Compatibility field; kingInCheck() is authoritative.

        self.white_can_castle_kingside = True
        self.white_can_castle_queenside = True
        self.black_can_castle_kingside = True
        self.black_can_castle_queenside = True

        self.en_passant_square: tuple[int, int] | None = None
        self.halfmove_clock = 0
        self.fullmove_number = 1
        self.move_history: list[Move] = []

        self._rebuild_fast_state()
        self.zobrist_hash = self.calculateZobristHash()

        # Repetition uses the compact incremental hash instead of a large tuple.
        self.position_history: list[int] = [self.zobrist_hash]

    def loadFen(self, fen: str) -> None:
        """Load a standard FEN string and rebuild all fast lookup structures."""
        fields = fen.strip().split()
        if len(fields) < 4:
            raise ValueError("FEN must contain at least board, side, castling, and en-passant fields")

        board_field, side_field, castling_field, ep_field = fields[:4]
        halfmove_field = fields[4] if len(fields) > 4 else "0"
        fullmove_field = fields[5] if len(fields) > 5 else "1"

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

        for piece_name in self.PIECE_NAMES:
            setattr(self, piece_name, 0)

        ranks = board_field.split("/")
        if len(ranks) != 8:
            raise ValueError("FEN board field must contain 8 ranks")

        # FEN lists rank 8 first; our bit 0 is a1.
        for fen_rank, row in enumerate(ranks):
            rank_index = 7 - fen_rank
            file_index = 0
            for char in row:
                if char.isdigit():
                    file_index += int(char)
                    continue
                if char not in piece_map or file_index >= 8:
                    raise ValueError(f"Invalid FEN board field: {board_field}")
                square = _coords_to_index(rank_index, file_index)
                piece_name = piece_map[char]
                setattr(self, piece_name, getattr(self, piece_name) | SQUARE_MASKS[square])
                file_index += 1
            if file_index != 8:
                raise ValueError(f"Invalid FEN rank: {row}")

        if side_field not in ("w", "b"):
            raise ValueError("FEN side-to-move field must be 'w' or 'b'")
        self.white_to_move = side_field == "w"

        self.white_can_castle_kingside = "K" in castling_field
        self.white_can_castle_queenside = "Q" in castling_field
        self.black_can_castle_kingside = "k" in castling_field
        self.black_can_castle_queenside = "q" in castling_field

        if ep_field == "-":
            self.en_passant_square = None
        else:
            if len(ep_field) != 2 or ep_field[0] not in "abcdefgh" or ep_field[1] not in "12345678":
                raise ValueError(f"Invalid FEN en-passant square: {ep_field}")
            self.en_passant_square = (int(ep_field[1]), ord(ep_field[0]) - ord("a") + 1)

        self.halfmove_clock = int(halfmove_field)
        self.fullmove_number = int(fullmove_field)
        self.move_history = []
        self.king_in_check = False

        self._rebuild_fast_state()
        self.zobrist_hash = self.calculateZobristHash()
        self.position_history = [self.zobrist_hash]

    # ------------------------------------------------------------------
    # Square conversion and position identity
    # ------------------------------------------------------------------

    @staticmethod
    def squareMask(rank: int, file: int) -> int:
        return SQUARE_MASKS[_public_to_index(rank, file)]

    @staticmethod
    def bitboardToSquare(bitboard: int) -> tuple[int, int]:
        if bitboard == 0 or bitboard & (bitboard - 1):
            raise ValueError("Bitboard must contain exactly one set bit")
        return _index_to_public(bitboard.bit_length() - 1)

    def positionKey(self) -> tuple:
        """Return a full rule-relevant key for debugging/compatibility.

        Repetition tracking itself uses ``zobrist_hash`` because it is much
        cheaper to append and compare during search.
        """
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

    def calculateZobristHash(self) -> int:
        """Calculate a hash from scratch.

        Search moves update the hash incrementally; this full calculation is
        used for reset/FEN loading and is also useful for debugging.
        """
        zobrist_hash = 0

        for piece_name in self.PIECE_NAMES:
            bitboard = getattr(self, piece_name)
            while bitboard:
                piece_bit = bitboard & -bitboard
                square = piece_bit.bit_length() - 1
                zobrist_hash ^= PIECE_KEYS[piece_name][square]
                bitboard ^= piece_bit

        if not self.white_to_move:
            zobrist_hash ^= SIDE_TO_MOVE_KEY

        if self.white_can_castle_kingside:
            zobrist_hash ^= CASTLING_KEYS["white_kingside"]
        if self.white_can_castle_queenside:
            zobrist_hash ^= CASTLING_KEYS["white_queenside"]
        if self.black_can_castle_kingside:
            zobrist_hash ^= CASTLING_KEYS["black_kingside"]
        if self.black_can_castle_queenside:
            zobrist_hash ^= CASTLING_KEYS["black_queenside"]

        if self.en_passant_square is not None:
            _, file = self.en_passant_square
            zobrist_hash ^= EN_PASSANT_KEYS[file - 1]

        return zobrist_hash

    # ------------------------------------------------------------------
    # O(1) piece lookup
    # ------------------------------------------------------------------

    def pieceColor(self, rank: int, file: int) -> str | None:
        piece = self.board[_public_to_index(rank, file)]
        if piece is None:
            return None
        return "w" if piece.startswith("white") else "b"

    def getPiece(self, rank: int, file: int) -> str | None:
        return self.board[_public_to_index(rank, file)]

    # ------------------------------------------------------------------
    # Fast sliding attacks
    # ------------------------------------------------------------------

    @staticmethod
    def _ray_attacks(square: int, occupied: int, direction: tuple[int, int]) -> int:
        """Return a ray up to and including its first blocker.

        The old implementation walked one square at a time. Here we intersect
        a precomputed ray with occupancy, identify the nearest blocker with one
        bit operation, then trim everything beyond that blocker.
        """
        ray = RAYS[direction][square]
        blockers = ray & occupied
        if not blockers:
            return ray

        delta = DIRECTION_DELTAS[direction]
        blocker_square = _lsb_square(blockers) if delta > 0 else _msb_square(blockers)
        return ray ^ RAYS[direction][blocker_square]

    @classmethod
    def _sliding_attacks(
        cls,
        square: int,
        occupied: int,
        directions: tuple[tuple[int, int], ...],
    ) -> int:
        attacks = 0
        for direction in directions:
            attacks |= cls._ray_attacks(square, occupied, direction)
        return attacks

    @classmethod
    def rookAttacks(cls, square: int, occupied: int) -> int:
        return cls._sliding_attacks(square, occupied, ROOK_DIRECTIONS)

    @classmethod
    def bishopAttacks(cls, square: int, occupied: int) -> int:
        return cls._sliding_attacks(square, occupied, BISHOP_DIRECTIONS)

    @classmethod
    def queenAttacks(cls, square: int, occupied: int) -> int:
        return cls._sliding_attacks(square, occupied, QUEEN_DIRECTIONS)

    # ------------------------------------------------------------------
    # Attack detection
    # ------------------------------------------------------------------

    def _attackers_to_index(
        self,
        square: int,
        attacking_color: str,
        occupied: int | None = None,
        ignore_attackers: int = 0,
    ) -> int:
        """Return all pieces of ``attacking_color`` attacking ``square``.

        ``occupied`` can describe a hypothetical king/en-passant position
        without mutating the whole GameState. ``ignore_attackers`` removes a
        hypothetically captured enemy piece from the attacker sets.
        """
        if attacking_color not in ("w", "b"):
            raise ValueError("attacking_color must be 'w' or 'b'")

        occupied = self.all_occupied if occupied is None else occupied
        keep = FULL_BOARD ^ ignore_attackers

        if attacking_color == "w":
            pawns = self.white_pawns & keep
            knights = self.white_knights & keep
            bishops = self.white_bishops & keep
            rooks = self.white_rooks & keep
            queens = self.white_queens & keep
            kings = self.white_kings & keep

            # Squares from which a white pawn attacks the target are the target's
            # black-pawn attack mask (the inverse movement direction).
            pawn_sources = BLACK_PAWN_ATTACKS[square]
        else:
            pawns = self.black_pawns & keep
            knights = self.black_knights & keep
            bishops = self.black_bishops & keep
            rooks = self.black_rooks & keep
            queens = self.black_queens & keep
            kings = self.black_kings & keep
            pawn_sources = WHITE_PAWN_ATTACKS[square]

        attackers = pawn_sources & pawns
        attackers |= KNIGHT_ATTACKS[square] & knights
        attackers |= KING_ATTACKS[square] & kings
        attackers |= self.bishopAttacks(square, occupied) & (bishops | queens)
        attackers |= self.rookAttacks(square, occupied) & (rooks | queens)
        return attackers

    def _is_square_attacked_index(
        self,
        square: int,
        attacking_color: str,
        occupied: int | None = None,
        ignore_attackers: int = 0,
    ) -> bool:
        return bool(
            self._attackers_to_index(
                square,
                attacking_color,
                occupied=occupied,
                ignore_attackers=ignore_attackers,
            )
        )

    def isSquareAttacked(self, rank: int, file: int, attacking_color: str) -> bool:
        return self._is_square_attacked_index(
            _public_to_index(rank, file),
            attacking_color,
        )

    def kingInCheck(self, king_color: str) -> bool:
        king_board = self.white_kings if king_color == "w" else self.black_kings
        if king_board == 0:
            # Malformed positions must never create legal king-capture lines.
            return True
        king_square = king_board.bit_length() - 1
        enemy = "b" if king_color == "w" else "w"
        return self._is_square_attacked_index(king_square, enemy)

    # ------------------------------------------------------------------
    # Check and pin analysis used by direct legal generation
    # ------------------------------------------------------------------

    def _checkers_and_pins(self, color: str) -> tuple[int, dict[int, int]]:
        """Return the checking pieces and movement masks for pinned pieces.

        A pinned piece may only remain on the line between its king and the
        pinning slider, including the slider's square (capture). Knights pinned
        to a king naturally end up with zero legal destinations after this mask.
        """
        king_board = self.white_kings if color == "w" else self.black_kings
        if king_board == 0:
            return FULL_BOARD, {}

        king_square = king_board.bit_length() - 1
        enemy = "b" if color == "w" else "w"
        friendly = self.white_occupied if color == "w" else self.black_occupied

        checkers = self._attackers_to_index(king_square, enemy)
        pins: dict[int, int] = {}

        enemy_rook_queen = (
            (self.black_rooks | self.black_queens)
            if enemy == "b"
            else (self.white_rooks | self.white_queens)
        )
        enemy_bishop_queen = (
            (self.black_bishops | self.black_queens)
            if enemy == "b"
            else (self.white_bishops | self.white_queens)
        )

        for direction in QUEEN_DIRECTIONS:
            ray_blockers = RAYS[direction][king_square] & self.all_occupied
            if not ray_blockers:
                continue

            delta = DIRECTION_DELTAS[direction]
            first_square = _lsb_square(ray_blockers) if delta > 0 else _msb_square(ray_blockers)
            first_bit = SQUARE_MASKS[first_square]

            # A pin requires the first blocker to be friendly.
            if not (first_bit & friendly):
                continue

            beyond = RAYS[direction][first_square] & self.all_occupied
            if not beyond:
                continue

            second_square = _lsb_square(beyond) if delta > 0 else _msb_square(beyond)
            second_bit = SQUARE_MASKS[second_square]
            sliders = enemy_bishop_queen if direction in BISHOP_DIRECTIONS else enemy_rook_queen

            if second_bit & sliders:
                pins[first_square] = BETWEEN[king_square][second_square] | second_bit

        return checkers, pins

    # ------------------------------------------------------------------
    # Draw / terminal helpers
    # ------------------------------------------------------------------

    def isCheckmate(self) -> bool:
        color = "w" if self.white_to_move else "b"
        return self.kingInCheck(color) and not self.generateMoves()

    def isStalemate(self) -> bool:
        color = "w" if self.white_to_move else "b"
        return not self.kingInCheck(color) and not self.generateMoves()

    def isFiftyMoveDraw(self) -> bool:
        return self.halfmove_clock >= 100

    def isThreefoldRepetition(self) -> bool:
        return self.position_history.count(self.zobrist_hash) >= 3

    def hasInsufficientMaterial(self) -> bool:
        if (
            self.white_pawns
            | self.black_pawns
            | self.white_rooks
            | self.black_rooks
            | self.white_queens
            | self.black_queens
        ):
            return False

        total_minors = (
            self.white_knights.bit_count()
            + self.black_knights.bit_count()
            + self.white_bishops.bit_count()
            + self.black_bishops.bit_count()
        )

        # This deliberately only auto-draws unambiguous dead positions.
        return total_minors <= 1

    def isDraw(self) -> bool:
        # Put cheap tests before stalemate because stalemate generates moves.
        return (
            self.isFiftyMoveDraw()
            or self.isThreefoldRepetition()
            or self.hasInsufficientMaterial()
            or self.isStalemate()
        )

    # ------------------------------------------------------------------
    # Incremental make / undo
    # ------------------------------------------------------------------

    def xorCastlingHash(self) -> None:
        if self.white_can_castle_kingside:
            self.zobrist_hash ^= CASTLING_KEYS["white_kingside"]
        if self.white_can_castle_queenside:
            self.zobrist_hash ^= CASTLING_KEYS["white_queenside"]
        if self.black_can_castle_kingside:
            self.zobrist_hash ^= CASTLING_KEYS["black_kingside"]
        if self.black_can_castle_queenside:
            self.zobrist_hash ^= CASTLING_KEYS["black_queenside"]

    def xorEnPassantHash(self) -> None:
        if self.en_passant_square is not None:
            _, file = self.en_passant_square
            self.zobrist_hash ^= EN_PASSANT_KEYS[file - 1]

    def _move_occupancy(self, color: str, start_bit: int, end_bit: int) -> None:
        """Move one piece inside the cached occupancy bitboard."""
        if color == "w":
            self.white_occupied = (self.white_occupied & ~start_bit) | end_bit
        else:
            self.black_occupied = (self.black_occupied & ~start_bit) | end_bit

    def _remove_occupancy(self, color: str, bit: int) -> None:
        if color == "w":
            self.white_occupied &= ~bit
        else:
            self.black_occupied &= ~bit

    def _add_occupancy(self, color: str, bit: int) -> None:
        if color == "w":
            self.white_occupied |= bit
        else:
            self.black_occupied |= bit

    def movePiece(self, move: Move) -> bool:
        start_square = _public_to_index(move.start_rank, move.start_file)
        end_square = _public_to_index(move.end_rank, move.end_file)
        start_bit = SQUARE_MASKS[start_square]
        end_bit = SQUARE_MASKS[end_square]

        # Mailbox lookup is O(1), unlike the old 12-bitboard scan.
        move.moved_piece = self.board[start_square]
        if move.moved_piece is None:
            return False

        moving_color = "w" if move.moved_piece.startswith("white") else "b"
        if moving_color != ("w" if self.white_to_move else "b"):
            return False

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

        # Infer special flags for callers that manually construct Move objects.
        if "kings" in move.moved_piece and abs(move.end_file - move.start_file) == 2:
            move.is_castle = True
        if (
            "pawns" in move.moved_piece
            and move.start_file != move.end_file
            and self.board[end_square] is None
            and self.en_passant_square == (move.end_rank, move.end_file)
        ):
            move.is_en_passant = True

        if move.is_en_passant:
            capture_square = _public_to_index(move.start_rank, move.end_file)
        else:
            capture_square = end_square

        capture_bit = SQUARE_MASKS[capture_square]
        move.captured_square = _index_to_public(capture_square)
        move.captured_piece = self.board[capture_square]

        # Remove old rule-state keys before changing those fields.
        self.xorCastlingHash()
        self.xorEnPassantHash()

        # Moving piece leaves the start square.
        self.zobrist_hash ^= PIECE_KEYS[move.moved_piece][start_square]

        if move.captured_piece is not None:
            captured_color = "w" if move.captured_piece.startswith("white") else "b"
            self.zobrist_hash ^= PIECE_KEYS[move.captured_piece][capture_square]
            setattr(
                self,
                move.captured_piece,
                getattr(self, move.captured_piece) & ~capture_bit,
            )
            self.board[capture_square] = None
            self._remove_occupancy(captured_color, capture_bit)

        # Update the moving piece bitboard and mailbox. Promotion swaps the pawn
        # for the promoted piece at the destination.
        moving_board = getattr(self, move.moved_piece) & ~start_bit
        self.board[start_square] = None

        if move.promotion is not None:
            setattr(self, move.moved_piece, moving_board)
            setattr(self, move.promotion, getattr(self, move.promotion) | end_bit)
            self.board[end_square] = move.promotion
            self.zobrist_hash ^= PIECE_KEYS[move.promotion][end_square]
        else:
            moving_board |= end_bit
            setattr(self, move.moved_piece, moving_board)
            self.board[end_square] = move.moved_piece
            self.zobrist_hash ^= PIECE_KEYS[move.moved_piece][end_square]

        self._move_occupancy(moving_color, start_bit, end_bit)

        # Castling moves a rook as part of the same move.
        if move.is_castle:
            rook_name = "white_rooks" if moving_color == "w" else "black_rooks"
            rook_start_file = 8 if move.end_file > move.start_file else 1
            rook_end_file = 6 if move.end_file > move.start_file else 4
            rook_start_square = _public_to_index(move.start_rank, rook_start_file)
            rook_end_square = _public_to_index(move.start_rank, rook_end_file)
            self.zobrist_hash ^= PIECE_KEYS[rook_name][rook_start_square]
            self.zobrist_hash ^= PIECE_KEYS[rook_name][rook_end_square]
            self._move_castling_rook(move, undo=False)

        self._update_castling_rights(move)

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

        self.all_occupied = self.white_occupied | self.black_occupied

        # Add new rule-state keys, then flip side-to-move in the hash/state.
        self.xorCastlingHash()
        self.xorEnPassantHash()
        self.zobrist_hash ^= SIDE_TO_MOVE_KEY

        self.move_history.append(move)
        self.white_to_move = not self.white_to_move
        self.position_history.append(self.zobrist_hash)
        return True

    def undoMove(self, move: Move | None = None) -> bool:
        if not self.move_history:
            return False
        if move is None:
            move = self.move_history[-1]
        if move.moved_piece is None or move.previous_state is None:
            raise ValueError("Move does not contain undo state")

        start_square = _public_to_index(move.start_rank, move.start_file)
        end_square = _public_to_index(move.end_rank, move.end_file)
        start_bit = SQUARE_MASKS[start_square]
        end_bit = SQUARE_MASKS[end_square]
        moving_color = "w" if move.moved_piece.startswith("white") else "b"

        if move.is_castle:
            self._move_castling_rook(move, undo=True)

        # Remove the moved/promoted piece from the destination and restore the
        # original moving piece on its start square.
        if move.promotion is not None:
            setattr(self, move.promotion, getattr(self, move.promotion) & ~end_bit)
            setattr(self, move.moved_piece, getattr(self, move.moved_piece) | start_bit)
        else:
            moving_board = getattr(self, move.moved_piece)
            moving_board = (moving_board & ~end_bit) | start_bit
            setattr(self, move.moved_piece, moving_board)

        self.board[end_square] = None
        self.board[start_square] = move.moved_piece
        self._move_occupancy(moving_color, end_bit, start_bit)

        # Restore any captured piece, including an en-passant pawn whose capture
        # square differs from the move destination.
        if move.captured_piece is not None and move.captured_square is not None:
            capture_square = _public_to_index(*move.captured_square)
            capture_bit = SQUARE_MASKS[capture_square]
            captured_color = "w" if move.captured_piece.startswith("white") else "b"
            setattr(
                self,
                move.captured_piece,
                getattr(self, move.captured_piece) | capture_bit,
            )
            self.board[capture_square] = move.captured_piece
            self._add_occupancy(captured_color, capture_bit)

        self.all_occupied = self.white_occupied | self.black_occupied

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
        color = "w" if move.moved_piece and move.moved_piece.startswith("white") else "b"
        rook_name = "white_rooks" if color == "w" else "black_rooks"
        rank = move.start_rank

        if move.end_file > move.start_file:
            rook_start_file, rook_end_file = 8, 6
        else:
            rook_start_file, rook_end_file = 1, 4

        if undo:
            source_file, destination_file = rook_end_file, rook_start_file
        else:
            source_file, destination_file = rook_start_file, rook_end_file

        source_square = _public_to_index(rank, source_file)
        destination_square = _public_to_index(rank, destination_file)
        source_bit = SQUARE_MASKS[source_square]
        destination_bit = SQUARE_MASKS[destination_square]

        rook_board = getattr(self, rook_name)
        rook_board = (rook_board & ~source_bit) | destination_bit
        setattr(self, rook_name, rook_board)

        self.board[source_square] = None
        self.board[destination_square] = rook_name
        self._move_occupancy(color, source_bit, destination_bit)

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

    # ------------------------------------------------------------------
    # Move construction helpers
    # ------------------------------------------------------------------

    def _createMove(
        self,
        start_rank: int,
        start_file: int,
        end_rank: int,
        end_file: int,
        promotion: str | None = None,
        piece_name: str | None = None,
    ) -> Move:
        """Create a move using O(1) mailbox lookups for special flags."""
        start_square = _public_to_index(start_rank, start_file)
        end_square = _public_to_index(end_rank, end_file)
        piece_name = self.board[start_square] if piece_name is None else piece_name

        is_castle = bool(
            piece_name
            and "kings" in piece_name
            and abs(end_file - start_file) == 2
        )
        is_en_passant = bool(
            piece_name
            and "pawns" in piece_name
            and start_file != end_file
            and self.board[end_square] is None
            and self.en_passant_square == (end_rank, end_file)
        )

        if is_en_passant:
            captured_square = _public_to_index(start_rank, end_file)
        else:
            captured_square = end_square

        return Move(
            start_rank,
            start_file,
            end_rank,
            end_file,
            promotion=promotion,
            is_castle=is_castle,
            is_en_passant=is_en_passant,
            moved_piece=piece_name,
            captured_piece=self.board[captured_square],
            captured_square=_index_to_public(captured_square),
        )

    def _createMoveFromSquares(
        self,
        start_square: int,
        end_square: int,
        piece_name: str,
        promotion: str | None = None,
        is_castle: bool = False,
        is_en_passant: bool = False,
    ) -> Move:
        """Fast square-indexed constructor used by the search move generator."""
        start_rank, start_file = _index_to_public(start_square)
        end_rank, end_file = _index_to_public(end_square)

        if is_en_passant:
            captured_square = _public_to_index(start_rank, end_file)
        else:
            captured_square = end_square

        return Move(
            start_rank,
            start_file,
            end_rank,
            end_file,
            promotion=promotion,
            is_castle=is_castle,
            is_en_passant=is_en_passant,
            moved_piece=piece_name,
            captured_piece=self.board[captured_square],
            captured_square=_index_to_public(captured_square),
        )

    def _append_destinations(
        self,
        moves: list[Move],
        start_square: int,
        destinations: int,
        piece_name: str,
    ) -> None:
        """Convert a destination bitboard into Move objects."""
        enemy_king = self.black_kings if piece_name.startswith("white") else self.white_kings
        destinations &= ~enemy_king

        while destinations:
            destination_bit = destinations & -destinations
            end_square = destination_bit.bit_length() - 1

            if "pawns" in piece_name and (end_square >> 3) in (0, 7):
                prefix = "white" if piece_name.startswith("white") else "black"
                for promotion_piece in ("queens", "knights", "bishops", "rooks"):
                    moves.append(
                        self._createMoveFromSquares(
                            start_square,
                            end_square,
                            piece_name,
                            promotion=f"{prefix}_{promotion_piece}",
                        )
                    )
            else:
                moves.append(
                    self._createMoveFromSquares(start_square, end_square, piece_name)
                )

            destinations ^= destination_bit

    # ------------------------------------------------------------------
    # Fast pseudo-move helpers
    # ------------------------------------------------------------------

    def _pawn_moves_from_square(self, square: int, color: str) -> tuple[int, int]:
        """Return (ordinary destinations, en-passant destinations) for a pawn."""
        rank = square >> 3
        direction = 8 if color == "w" else -8
        start_rank = 1 if color == "w" else 6
        enemy = self.black_occupied if color == "w" else self.white_occupied
        attacks = WHITE_PAWN_ATTACKS[square] if color == "w" else BLACK_PAWN_ATTACKS[square]

        normal = attacks & enemy
        en_passant = 0

        one_square = square + direction
        if 0 <= one_square < 64:
            one_bit = SQUARE_MASKS[one_square]
            if not (one_bit & self.all_occupied):
                normal |= one_bit
                if rank == start_rank:
                    two_square = square + 2 * direction
                    two_bit = SQUARE_MASKS[two_square]
                    if not (two_bit & self.all_occupied):
                        normal |= two_bit

        if self.en_passant_square is not None:
            ep_square = _public_to_index(*self.en_passant_square)
            ep_bit = SQUARE_MASKS[ep_square]
            if attacks & ep_bit:
                en_passant = ep_bit

        return normal, en_passant

    def _pseudo_destinations(self, square: int, piece_name: str) -> tuple[int, int]:
        """Return (ordinary, en-passant) destination masks for one piece."""
        color = "w" if piece_name.startswith("white") else "b"
        friendly = self.white_occupied if color == "w" else self.black_occupied

        if "pawns" in piece_name:
            return self._pawn_moves_from_square(square, color)
        if "knights" in piece_name:
            return KNIGHT_ATTACKS[square] & ~friendly & FULL_BOARD, 0
        if "bishops" in piece_name:
            return self.bishopAttacks(square, self.all_occupied) & ~friendly, 0
        if "rooks" in piece_name:
            return self.rookAttacks(square, self.all_occupied) & ~friendly, 0
        if "queens" in piece_name:
            return self.queenAttacks(square, self.all_occupied) & ~friendly, 0
        if "kings" in piece_name:
            return KING_ATTACKS[square] & ~friendly & FULL_BOARD, 0
        return 0, 0

    # ------------------------------------------------------------------
    # Public per-piece pseudo-move API
    # ------------------------------------------------------------------

    def getPseudoLegalMoves(self, rank: int, file: int) -> int:
        square = _public_to_index(rank, file)
        piece_name = self.board[square]
        if piece_name is None:
            return 0

        ordinary, en_passant = self._pseudo_destinations(square, piece_name)
        moves = ordinary | en_passant

        if "kings" in piece_name:
            color = "w" if piece_name.startswith("white") else "b"
            if self._canCastle(color, kingside=True):
                moves |= SQUARE_MASKS[_public_to_index(rank, 7)]
            if self._canCastle(color, kingside=False):
                moves |= SQUARE_MASKS[_public_to_index(rank, 3)]

        return moves

    def getLegalMoves(self, rank: int, file: int) -> int:
        """Return legal destination bits for one source square.

        This wrapper is mainly for the GUI. Search calls ``generateMoves()``
        once and receives the full legal move list directly.
        """
        legal = 0
        for move in self.generateMoves():
            if move.start_rank == rank and move.start_file == file:
                legal |= self.squareMask(move.end_rank, move.end_file)
        return legal

    def getKnightMoves(self, rank: int, file: int) -> int:
        square = _public_to_index(rank, file)
        piece = self.board[square]
        if piece is None:
            return 0
        color = "w" if piece.startswith("white") else "b"
        friendly = self.white_occupied if color == "w" else self.black_occupied
        return KNIGHT_ATTACKS[square] & ~friendly & FULL_BOARD

    def getPawnMoves(self, rank: int, file: int) -> int:
        square = _public_to_index(rank, file)
        piece = self.board[square]
        if piece is None:
            return 0
        color = "w" if piece.startswith("white") else "b"
        ordinary, en_passant = self._pawn_moves_from_square(square, color)
        return ordinary | en_passant

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
        square = _public_to_index(rank, file)
        piece = self.board[square]
        if piece is None:
            return 0
        color = "w" if piece.startswith("white") else "b"
        friendly = self.white_occupied if color == "w" else self.black_occupied
        return self._sliding_attacks(square, self.all_occupied, directions) & ~friendly

    def slidingMoves(
        self,
        rank: int,
        file: int,
        friendly_pieces: int,
        enemy_pieces: int,
        directions: tuple[tuple[int, int], ...],
    ) -> int:
        """Compatibility wrapper around the new precomputed-ray slider logic."""
        square = _public_to_index(rank, file)
        occupied = friendly_pieces | enemy_pieces
        return self._sliding_attacks(square, occupied, directions) & ~friendly_pieces

    def getKingMoves(self, rank: int, file: int) -> int:
        square = _public_to_index(rank, file)
        piece = self.board[square]
        if piece is None:
            return 0
        color = "w" if piece.startswith("white") else "b"
        friendly = self.white_occupied if color == "w" else self.black_occupied
        moves = KING_ATTACKS[square] & ~friendly & FULL_BOARD

        if self._canCastle(color, kingside=True):
            moves |= SQUARE_MASKS[_public_to_index(rank, 7)]
        if self._canCastle(color, kingside=False):
            moves |= SQUARE_MASKS[_public_to_index(rank, 3)]
        return moves

    # ------------------------------------------------------------------
    # Castling
    # ------------------------------------------------------------------

    def _canCastle(self, color: str | None, kingside: bool) -> bool:
        if color not in ("w", "b"):
            return False

        rank = 1 if color == "w" else 8
        king_name = "white_kings" if color == "w" else "black_kings"
        rook_name = "white_rooks" if color == "w" else "black_rooks"
        enemy = "b" if color == "w" else "w"

        if color == "w":
            has_right = (
                self.white_can_castle_kingside
                if kingside
                else self.white_can_castle_queenside
            )
        else:
            has_right = (
                self.black_can_castle_kingside
                if kingside
                else self.black_can_castle_queenside
            )
        if not has_right:
            return False

        king_square = _public_to_index(rank, 5)
        if not (getattr(self, king_name) & SQUARE_MASKS[king_square]):
            return False

        rook_file = 8 if kingside else 1
        rook_square = _public_to_index(rank, rook_file)
        if not (getattr(self, rook_name) & SQUARE_MASKS[rook_square]):
            return False

        empty_files = (6, 7) if kingside else (2, 3, 4)
        for file in empty_files:
            if self.all_occupied & SQUARE_MASKS[_public_to_index(rank, file)]:
                return False

        # The king may not start in check, cross an attacked square, or land on
        # one. Test transit positions using only occupancy changes rather than a
        # full make/undo cycle.
        transit_files = (5, 6, 7) if kingside else (5, 4, 3)
        king_bit = SQUARE_MASKS[king_square]
        occupied_without_king = self.all_occupied & ~king_bit

        for file in transit_files:
            square = _public_to_index(rank, file)
            occupied = occupied_without_king | SQUARE_MASKS[square]
            if self._is_square_attacked_index(square, enemy, occupied=occupied):
                return False

        return True

    # ------------------------------------------------------------------
    # Direct legal move generation
    # ------------------------------------------------------------------

    def _is_en_passant_legal(
        self,
        start_square: int,
        end_square: int,
        color: str,
        king_square: int,
    ) -> bool:
        """Check en-passant king safety with a tiny occupancy simulation.

        En-passant is special because two squares become empty at once (the
        moving pawn's start and the captured pawn's square). That can reveal a
        rook/bishop/queen attack which ordinary pin masks cannot represent.
        """
        start_rank = start_square >> 3
        end_file = end_square & 7
        captured_square = _coords_to_index(start_rank, end_file)

        start_bit = SQUARE_MASKS[start_square]
        end_bit = SQUARE_MASKS[end_square]
        captured_bit = SQUARE_MASKS[captured_square]

        occupied_after = self.all_occupied
        occupied_after &= ~start_bit
        occupied_after &= ~captured_bit
        occupied_after |= end_bit

        enemy = "b" if color == "w" else "w"
        return not self._is_square_attacked_index(
            king_square,
            enemy,
            occupied=occupied_after,
            ignore_attackers=captured_bit,
        )

    def _append_legal_nonking_moves(
        self,
        moves: list[Move],
        piece_name: str,
        bitboard: int,
        pins: dict[int, int],
        evasion_mask: int,
        check_count: int,
    ) -> None:
        """Generate legal moves for one non-king piece type."""
        if check_count >= 2:
            return

        color = "w" if piece_name.startswith("white") else "b"
        king_board = self.white_kings if color == "w" else self.black_kings
        king_square = king_board.bit_length() - 1

        while bitboard:
            piece_bit = bitboard & -bitboard
            start_square = piece_bit.bit_length() - 1
            ordinary, en_passant = self._pseudo_destinations(start_square, piece_name)

            # Ordinary moves are legal if they stay on a pin line (when pinned)
            # and, in single check, capture/block the checker.
            if start_square in pins:
                ordinary &= pins[start_square]
            if check_count == 1:
                ordinary &= evasion_mask

            self._append_destinations(moves, start_square, ordinary, piece_name)

            # En-passant bypasses the normal pin/evasion mask and performs the
            # exact occupancy king-safety test instead. This correctly handles
            # capturing a checking pawn and blocking/revealing slider attacks.
            while en_passant:
                destination_bit = en_passant & -en_passant
                end_square = destination_bit.bit_length() - 1
                if self._is_en_passant_legal(
                    start_square,
                    end_square,
                    color,
                    king_square,
                ):
                    moves.append(
                        self._createMoveFromSquares(
                            start_square,
                            end_square,
                            piece_name,
                            is_en_passant=True,
                        )
                    )
                en_passant ^= destination_bit

            bitboard ^= piece_bit

    def _append_legal_king_moves(
        self,
        moves: list[Move],
        color: str,
        check_count: int,
    ) -> None:
        king_name = "white_kings" if color == "w" else "black_kings"
        king_board = getattr(self, king_name)
        if king_board == 0:
            return

        king_square = king_board.bit_length() - 1
        king_bit = SQUARE_MASKS[king_square]
        friendly = self.white_occupied if color == "w" else self.black_occupied
        enemy_king = self.black_kings if color == "w" else self.white_kings
        enemy = "b" if color == "w" else "w"

        destinations = KING_ATTACKS[king_square] & ~friendly & ~enemy_king & FULL_BOARD

        while destinations:
            destination_bit = destinations & -destinations
            end_square = destination_bit.bit_length() - 1

            # Remove the king from its start square. The destination remains
            # occupied by the king even if an enemy piece was captured there.
            occupied_after = (self.all_occupied & ~king_bit) | destination_bit
            captured_enemy = destination_bit if destination_bit & (
                self.black_occupied if color == "w" else self.white_occupied
            ) else 0

            if not self._is_square_attacked_index(
                end_square,
                enemy,
                occupied=occupied_after,
                ignore_attackers=captured_enemy,
            ):
                moves.append(
                    self._createMoveFromSquares(
                        king_square,
                        end_square,
                        king_name,
                    )
                )

            destinations ^= destination_bit

        # Castling is impossible while currently in check. _canCastle() then
        # verifies rights, emptiness, and attack-free transit squares.
        if check_count == 0:
            rank = 1 if color == "w" else 8
            if self._canCastle(color, kingside=True):
                moves.append(
                    self._createMoveFromSquares(
                        king_square,
                        _public_to_index(rank, 7),
                        king_name,
                        is_castle=True,
                    )
                )
            if self._canCastle(color, kingside=False):
                moves.append(
                    self._createMoveFromSquares(
                        king_square,
                        _public_to_index(rank, 3),
                        king_name,
                        is_castle=True,
                    )
                )

    def generateMoves(self) -> list[Move]:
        """Generate legal moves directly, without make/check/undo filtering."""
        color = "w" if self.white_to_move else "b"
        enemy = "b" if color == "w" else "w"
        king_board = self.white_kings if color == "w" else self.black_kings
        if king_board == 0:
            return []

        king_square = king_board.bit_length() - 1
        checkers, pins = self._checkers_and_pins(color)
        check_count = checkers.bit_count()

        # In single check a non-king move must capture the checker or, when the
        # checker is a slider, block the line between checker and king.
        evasion_mask = FULL_BOARD
        if check_count == 1:
            checker_square = _lsb_square(checkers)
            checker_bit = SQUARE_MASKS[checker_square]
            enemy_sliders = (
                self.black_bishops
                | self.black_rooks
                | self.black_queens
                if enemy == "b"
                else self.white_bishops | self.white_rooks | self.white_queens
            )
            if checker_bit & enemy_sliders:
                evasion_mask = BETWEEN[king_square][checker_square] | checker_bit
            else:
                evasion_mask = checker_bit

        moves: list[Move] = []

        if color == "w":
            self._append_legal_nonking_moves(
                moves, "white_pawns", self.white_pawns, pins, evasion_mask, check_count
            )
            self._append_legal_nonking_moves(
                moves, "white_knights", self.white_knights, pins, evasion_mask, check_count
            )
            self._append_legal_nonking_moves(
                moves, "white_bishops", self.white_bishops, pins, evasion_mask, check_count
            )
            self._append_legal_nonking_moves(
                moves, "white_rooks", self.white_rooks, pins, evasion_mask, check_count
            )
            self._append_legal_nonking_moves(
                moves, "white_queens", self.white_queens, pins, evasion_mask, check_count
            )
        else:
            self._append_legal_nonking_moves(
                moves, "black_pawns", self.black_pawns, pins, evasion_mask, check_count
            )
            self._append_legal_nonking_moves(
                moves, "black_knights", self.black_knights, pins, evasion_mask, check_count
            )
            self._append_legal_nonking_moves(
                moves, "black_bishops", self.black_bishops, pins, evasion_mask, check_count
            )
            self._append_legal_nonking_moves(
                moves, "black_rooks", self.black_rooks, pins, evasion_mask, check_count
            )
            self._append_legal_nonking_moves(
                moves, "black_queens", self.black_queens, pins, evasion_mask, check_count
            )

        # In double check this is intentionally the only generator that adds moves.
        self._append_legal_king_moves(moves, color, check_count)
        return moves

    # ------------------------------------------------------------------
    # Compatibility pseudo generator / UI legality check
    # ------------------------------------------------------------------

    def generateMovesFromBitboard(self, bitboard: int, move_generator) -> list[Move]:
        """Legacy compatibility helper.

        The optimized search path does not use this function. It remains here so
        older GUI/evaluation code that calls it directly does not break.
        """
        moves: list[Move] = []
        while bitboard:
            piece_bit = bitboard & -bitboard
            start_square = piece_bit.bit_length() - 1
            start_rank, start_file = _index_to_public(start_square)
            piece_name = self.board[start_square]
            destinations = move_generator(start_rank, start_file)

            if piece_name is not None:
                self._append_destinations(moves, start_square, destinations, piece_name)
            bitboard ^= piece_bit
        return moves

    def generatePseudoMoves(self) -> list[Move]:
        """Generate pseudo-legal moves without king-safety filtering."""
        color = "w" if self.white_to_move else "b"
        piece_sets = (
            (
                ("white_pawns", self.white_pawns),
                ("white_knights", self.white_knights),
                ("white_bishops", self.white_bishops),
                ("white_rooks", self.white_rooks),
                ("white_queens", self.white_queens),
                ("white_kings", self.white_kings),
            )
            if color == "w"
            else (
                ("black_pawns", self.black_pawns),
                ("black_knights", self.black_knights),
                ("black_bishops", self.black_bishops),
                ("black_rooks", self.black_rooks),
                ("black_queens", self.black_queens),
                ("black_kings", self.black_kings),
            )
        )

        moves: list[Move] = []
        for piece_name, bitboard in piece_sets:
            remaining = bitboard
            while remaining:
                piece_bit = remaining & -remaining
                start_square = piece_bit.bit_length() - 1
                ordinary, en_passant = self._pseudo_destinations(start_square, piece_name)
                self._append_destinations(moves, start_square, ordinary, piece_name)

                while en_passant:
                    destination_bit = en_passant & -en_passant
                    end_square = destination_bit.bit_length() - 1
                    moves.append(
                        self._createMoveFromSquares(
                            start_square,
                            end_square,
                            piece_name,
                            is_en_passant=True,
                        )
                    )
                    en_passant ^= destination_bit

                remaining ^= piece_bit

        # Add castling pseudo-moves only when the full castling conditions hold;
        # this matches the behavior of the old getKingMoves().
        king_board = self.white_kings if color == "w" else self.black_kings
        if king_board:
            king_square = king_board.bit_length() - 1
            king_name = "white_kings" if color == "w" else "black_kings"
            rank = 1 if color == "w" else 8
            if self._canCastle(color, kingside=True):
                moves.append(
                    self._createMoveFromSquares(
                        king_square,
                        _public_to_index(rank, 7),
                        king_name,
                        is_castle=True,
                    )
                )
            if self._canCastle(color, kingside=False):
                moves.append(
                    self._createMoveFromSquares(
                        king_square,
                        _public_to_index(rank, 3),
                        king_name,
                        is_castle=True,
                    )
                )

        return moves

    def moveIsLegal(self, move: Move) -> bool:
        """Validate a UI/user move against the directly generated legal list."""
        for legal_move in self.generateMoves():
            if (
                legal_move.start_rank == move.start_rank
                and legal_move.start_file == move.start_file
                and legal_move.end_rank == move.end_rank
                and legal_move.end_file == move.end_file
            ):
                if move.promotion is not None and move.promotion != legal_move.promotion:
                    continue
                # Unspecified promotion defaults to a queen for UI callers.
                if (
                    move.promotion is None
                    and legal_move.promotion
                    and "queens" not in legal_move.promotion
                ):
                    continue

                move.promotion = legal_move.promotion
                move.is_castle = legal_move.is_castle
                move.is_en_passant = legal_move.is_en_passant
                move.moved_piece = legal_move.moved_piece
                move.captured_piece = legal_move.captured_piece
                move.captured_square = legal_move.captured_square
                return True
        return False
