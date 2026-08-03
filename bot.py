import random
from board import GameState, Move
from evaluation import Evaluator


class Bot:
    def __init__(self, game : GameState):
        self.depth = 3
        self.game = game
        self.nodes = 0
        self.bestscore = 0
        self.piece_values = {
            "white_pawns": 100,
            "black_pawns": -100,
            "white_knights": 320,
            "black_knights": -320,
            "white_bishops": 330,
            "black_bishops": -330,
            "white_rooks": 500,
            "black_rooks": -500,
            "white_queens": 900,
            "black_queens": -900,
            "white_kings": 0,
            "black_kings": 0,
        }

    def playRandom(self):
        moves = self.game.generateMoves()
        return moves[random.randint(0, len(moves) - 1)]
    