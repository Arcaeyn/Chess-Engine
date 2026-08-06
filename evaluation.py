# evaluation.py
from board import GameState
import math

class Evaluator:
    def __init__(self, game : GameState):
        self.game = game
        self.piece_square_tables = {
    "pawnsMid": [
         0,   0,   0,   0,   0,   0,   0,   0,
        50,  50,  50,  50,  50,  50,  50,  50,
        10,  10,  20,  30,  30,  20,  10,  10,
         5,   5,  10,  25,  25,  10,   5,   5,
         0,   0,   0,  20,  20,   0,   0,   0,
         5,  -5, -10,   0,   0, -10,  -5,   5,
         5,  10,  10, -20, -20,  10,  10,   5,
         0,   0,   0,   0,   0,   0,   0,   0,
    ],

    "pawnsEnd": [
         0,   0,   0,   0,   0,   0,   0,   0,
        80,  80,  80,  80,  80,  80,  80,  80,
        50,  50,  50,  50,  50,  50,  50,  50,
        30,  30,  30,  30,  30,  30,  30,  30,
        20,  20,  20,  20,  20,  20,  20,  20,
        10,  10,  10,  10,  10,  10,  10,  10,
        10,  10,  10,  10,  10,  10,  10,  10,
         0,   0,   0,   0,   0,   0,   0,   0,
    ],

    "rooksMid": [
         0,  0,  0,  0,  0,  0,  0,  0,
         5, 10, 10, 10, 10, 10, 10,  5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
         0,  0,  0,  5,  5,  0,  0,  0,
    ],

    "knightsMid": [
        -50, -40, -30, -30, -30, -30, -40, -50,
        -40, -20,   0,   0,   0,   0, -20, -40,
        -30,   0,  10,  15,  15,  10,   0, -30,
        -30,   5,  15,  20,  20,  15,   5, -30,
        -30,   0,  15,  20,  20,  15,   0, -30,
        -30,   5,  10,  15,  15,  10,   5, -30,
        -40, -20,   0,   5,   5,   0, -20, -40,
        -50, -40, -30, -30, -30, -30, -40, -50,
    ],

    "bishopsMid": [
        -20, -10, -10, -10, -10, -10, -10, -20,
        -10,   0,   0,   0,   0,   0,   0, -10,
        -10,   0,   5,  10,  10,   5,   0, -10,
        -10,   5,   5,  10,  10,   5,   5, -10,
        -10,   0,  10,  10,  10,  10,   0, -10,
        -10,  10,  10,  10,  10,  10,  10, -10,
        -10,   5,   0,   0,   0,   0,   5, -10,
        -20, -10, -10, -10, -10, -10, -10, -20,
    ],

    "queensMid": [
        -20, -10, -10,  -5,  -5, -10, -10, -20,
        -10,   0,   0,   0,   0,   0,   0, -10,
        -10,   0,   5,   5,   5,   5,   0, -10,
         -5,   0,   5,   5,   5,   5,   0,  -5,
          0,   0,   5,   5,   5,   5,   0,  -5,
        -10,   5,   5,   5,   5,   5,   0, -10,
        -10,   0,   5,   0,   0,   0,   0, -10,
        -20, -10, -10,  -5,  -5, -10, -10, -20,
    ],

    "kingsMid": [
        -80, -70, -70, -70, -70, -70, -70, -80,
        -60, -60, -60, -60, -60, -60, -60, -60,
        -40, -50, -50, -60, -60, -50, -50, -40,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -20, -30, -30, -40, -40, -30, -30, -20,
        -10, -20, -20, -20, -20, -20, -20, -10,
         20,  20,  -5,  -5,  -5,  -5,  20,  20,
         20,  30,  10,   0,   0,  10,  30,  20,
    ],

    "kingsEnd": [
        -20, -10, -10, -10, -10, -10, -10, -20,
         -5,   0,   5,   5,   5,   5,   0,  -5,
        -10,  -5,  20,  30,  30,  20,  -5, -10,
        -15, -10,  35,  45,  45,  35, -10, -15,
        -20, -15,  30,  40,  40,  30, -15, -20,
        -25, -20,  20,  25,  25,  20, -20, -25,
        -30, -25,   0,   0,   0,   0, -25, -30,
        -50, -30, -30, -30, -30, -30, -30, -50,
    ]}
        self.piece_bitboards = {

        "white_pawns": self.game.white_pawns,
        "white_knights": self.game.white_knights,
        "white_bishops": self.game.white_bishops,
        "white_rooks": self.game.white_rooks,
        "white_queens": self.game.white_queens,
        "white_kings": self.game.white_kings,

        "black_pawns": self.game.black_pawns,
        "black_knights": self.game.black_knights,
        "black_bishops": self.game.black_bishops,
        "black_rooks": self.game.black_rooks,
        "black_queens": self.game.black_queens,
        "black_kings": self.game.black_kings}
        self.pst_entries = [
    ("white_pawns",   self.piece_square_tables["pawnsMid"],
                      self.piece_square_tables["pawnsEnd"], 1),

    ("black_pawns",   self.piece_square_tables["pawnsMid"],
                      self.piece_square_tables["pawnsEnd"], -1),

    ("white_knights", self.piece_square_tables["knightsMid"],
                      self.piece_square_tables["knightsMid"], 1),

    ("black_knights", self.piece_square_tables["knightsMid"],
                      self.piece_square_tables["knightsMid"], -1),

    ("white_bishops", self.piece_square_tables["bishopsMid"],
                      self.piece_square_tables["bishopsMid"], 1),

    ("black_bishops", self.piece_square_tables["bishopsMid"],
                      self.piece_square_tables["bishopsMid"], -1),

    ("white_rooks",   self.piece_square_tables["rooksMid"],
                      self.piece_square_tables["rooksMid"], 1),

    ("black_rooks",   self.piece_square_tables["rooksMid"],
                      self.piece_square_tables["rooksMid"], -1),

    ("white_queens",  self.piece_square_tables["queensMid"],
                      self.piece_square_tables["queensMid"], 1),

    ("black_queens",  self.piece_square_tables["queensMid"],
                      self.piece_square_tables["queensMid"], -1),

    ("white_kings",   self.piece_square_tables["kingsMid"],
                      self.piece_square_tables["kingsEnd"], 1),

    ("black_kings",   self.piece_square_tables["kingsMid"],
                      self.piece_square_tables["kingsEnd"], -1)]
    
    def evaluate(self, game):
        score = 0

        material = self.material()
        score += material
        score += self.piece_square()
        score += self.mopUp(material)
        #score += self.mobilty()

        return score

    def material(self):
        score = 0

        score += self.game.white_pawns.bit_count() * 100
        score -= self.game.black_pawns.bit_count() * 100

        score += self.game.white_knights.bit_count() * 320
        score -= self.game.black_knights.bit_count() * 320

        score += self.game.white_bishops.bit_count() * 330
        score -= self.game.black_bishops.bit_count() * 330

        score += self.game.white_rooks.bit_count() * 500
        score -= self.game.black_rooks.bit_count() * 500

        score += self.game.white_queens.bit_count() * 900
        score -= self.game.black_queens.bit_count() * 900

        return score

    def piece_square(self):
        mid_score = 0
        end_score = 0

        for attribute, mid_table, end_table, sign in self.pst_entries:
            bitboard = getattr(self.game, attribute)
            is_black = sign == -1

            while bitboard:
                square = (bitboard & -bitboard).bit_length() - 1
                table_square = square if is_black else square ^ 56

                mid_score += sign * mid_table[table_square]
                end_score += sign * end_table[table_square]

                bitboard &= bitboard - 1

        phase = self.game.occupied.bit_count()
        return (mid_score * phase + end_score * (32 - phase)) / 32

    def mobilty(self):
        mobility_weights = {
        "pawns": 0,
        "knights": 4,
        "bishops": 5,
        "rooks": 2,
        "queens": 1,
        "kings": 0}

        score = 0
        for piece_name, bitboard in self.piece_bitboards.items():
            while bitboard:
                weight = mobility_weights[piece_name.split("_", 1)[1]]
                if  weight > 0:
                    piece_bit = bitboard & -bitboard
                    rank, file = self.game.bitboardToSquare(piece_bit)
                    numLegalMoves = self.game.getLegalMoves(rank, file).bit_count()
                    score += numLegalMoves * (1 if piece_bit & self.game.white_pieces else -1) * weight
                    bitboard &= bitboard - 1

        return score

    def mopUp(self, material):
        bonus = 0
        if self.game.white_to_move:
            if material > 500 and self.game.occupied.bit_count() < 10:
                rankW, fileW = self.game.bitboardToSquare(self.game.white_kings)
                rankB, fileB = self.game.bitboardToSquare(self.game.black_kings)
                bonus = abs(math.sqrt((rankW - rankB) ** 2 + (fileW - fileB) ** 2)) * 10

                if self.game.kingInCheck("b"):
                    bonus += 50

        else:
            if material < -500 and self.game.occupied.bit_count() < 10:
                rankW, fileW = self.game.bitboardToSquare(self.game.white_kings)
                rankB, fileB = self.game.bitboardToSquare(self.game.black_kings)
                bonus = abs(math.sqrt((rankW - rankB) ** 2 + (fileW - fileB) ** 2)) * -10

                if self.game.kingInCheck("w"):
                    bonus -= 50
                


        return bonus
