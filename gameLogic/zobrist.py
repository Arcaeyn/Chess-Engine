import random

_rng = random.Random(123456789)

PIECE_NAMES = [
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

PIECE_KEYS = {
    piece: [_rng.getrandbits(64) for _ in range(64)]
    for piece in PIECE_NAMES
}

SIDE_TO_MOVE_KEY = _rng.getrandbits(64)

CASTLING_KEYS = {
    "white_kingside": _rng.getrandbits(64),
    "white_queenside": _rng.getrandbits(64),
    "black_kingside": _rng.getrandbits(64),
    "black_queenside": _rng.getrandbits(64),
}

EN_PASSANT_KEYS = [_rng.getrandbits(64) for _ in range(8)]