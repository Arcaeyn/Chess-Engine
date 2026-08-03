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
        self.evaluator = Evaluator()

    def playRandom(self):
        moves = self.game.generateMoves()
        return moves[random.randint(0, len(moves) - 1)]
    
    def search(self, depth):
        # Base case:
        # If we've reached the desired depth, simply evaluate the position.
        if depth == 0:
            return self.eval()   

        # Generate all legal moves from the current position.
        moves = self.game.generateMoves()

        # TODO:
        # What happens if there are NO legal moves?
        #
        # This is where you'll handle:
        # - Checkmate
        # - Stalemate

        # TODO:
        # Decide whether we're maximizing or minimizing.

        if self.game.white_to_move:
            best = -1000000

        else:
            best = 1000000

        for move in moves:

            # Make the move
            self.game.movePiece(move)

            # Ask:
            # "If my opponent now plays perfectly,
            # how good is this position?"
            score = self.search(depth - 1)

            # Restore the board
            self.game.undoMove(move)

            if self.game.white_to_move and score > best:
                best = score

            elif not self.game.white_to_move and score < best:
                best = score
        return best
    
    def search2(self, depth, alpha=-1000000, beta=1000000):
        # Base case
        if depth == 0:
            return self.eval2()

        moves = self.game.generateMoves()

        # TODO:
        # Handle checkmate/stalemate here

        # White maximizes
        if self.game.white_to_move:
            best = -1000000

            for move in moves:
                self.game.movePiece(move)
                score = self.search2(depth - 1, alpha, beta)
                self.game.undoMove(move)

                if score > best:
                    best = score

                alpha = max(alpha, best)

                # Beta cutoff
                if beta <= alpha:
                    break

            return best

        # Black minimizes
        else:
            best = 1000000

            for move in moves:
                self.game.movePiece(move)
                score = self.search2(depth - 1, alpha, beta)
                self.game.undoMove(move)

                if score < best:
                    best = score

                beta = min(beta, best)

                # Alpha cutoff
                if beta <= alpha:
                    break

            return best

    def playBestMove(self, depth):
        moves = self.game.generateMoves()
        if self.game.white_to_move:
            best = -1000000

        else:
            best = 100000


        best_moves = []
        for move in moves:
            self.game.movePiece(move)
            score = self.search(depth - 1)
            self.game.undoMove(move)

            if score >= best and self.game.white_to_move:
                best = score
                best_moves = [move]

            elif score <= best and not self.game.white_to_move:
                best = score
                best_moves = [move]

            elif score == best:
                best_moves.append(move)

        print("My Eval: " + str(best))
        return best_moves[random.randint(0, len(best_moves) - 1)]

    def playBestMove2(self, depth):

        alpha = -1000000
        beta = 1000000

        moves = self.game.generateMoves()
        if self.game.white_to_move:
            best = -1000000

        else:
            best = 100000


        best_moves = []
        for move in moves:
            self.game.movePiece(move)
            score = self.search2(depth - 1, alpha, beta)
            self.game.undoMove(move)

            if score > best and self.game.white_to_move:
                best = score
                best_moves = [move]
                alpha = max(alpha, best)

            elif score < best and not self.game.white_to_move:
                best = score
                best_moves = [move]
                beta = min(beta, best)

            elif score == best:
                best_moves.append(move)

        print("Noam Eval: " + str(best))
        return best_moves[random.randint(0, len(best_moves) - 1)]

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

    def eval2(self):
        return self.evaluator.evaluate(self.game)