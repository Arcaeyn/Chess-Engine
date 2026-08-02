import random
from board import GameState, Move


class Bot:
    def __init__(self, game : GameState):
        self.depth = 3
        self.game = game
        self.nodes = 0
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
    
    
    def search(self, depth, alpha, beta):
        self.nodes += 1

        if depth == 0:
            return self.eval()

        moves = self.game.generateMoves()

        if not moves:
            return self.eval()

        if self.game.white_to_move:

            value = -100000

            for move in moves:
                self.game.movePiece(move)

                value = max(
                    value,
                    self.search(depth - 1, alpha, beta)
                )

                self.game.undoMove(move)

                alpha = max(alpha, value)

                if alpha >= beta:
                    break

            return value

        else:

            value = 100000

            for move in moves:
                self.game.movePiece(move)

                value = min(
                    value,
                    self.search(depth - 1, alpha, beta)
                )

                self.game.undoMove(move)

                beta = min(beta, value)

                if beta <= alpha:
                    break

            return value

    def findBestMove(self, depth):
        moves = self.game.generateMoves()

        best_move = None

        alpha = -100000
        beta = 100000

        if self.game.white_to_move:

            best_score = -100000

            for move in moves:
                self.game.movePiece(move)

                score = self.search(depth - 1, alpha, beta)

                self.game.undoMove(move)

                if score > best_score:
                    best_score = score
                    best_move = move

                alpha = max(alpha, best_score)

        else:

            best_score = 100000

            for move in moves:
                self.game.movePiece(move)

                score = self.search(depth - 1, alpha, beta)

                self.game.undoMove(move)

                if score < best_score:
                    best_score = score
                    best_move = move

                beta = min(beta, best_score)

        print(self.nodes)
        self.nodes = 0

        return best_move
    
    def eval(self):
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

