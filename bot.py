import random
from board import GameState, Move
from evaluation import Evaluator
import time

QDEPTHMAX = 5

class Bot:
    def __init__(self, game : GameState):
        self.depth = 3
        self.game = game
        self.nodes = 0
        self.evaluator = Evaluator(self.game)
        self.bestscore = 0
        self.eval = 0
        self.qnodes = 1
        self.qmax = 0
        self.qavg = 0
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
    
    def miniMax(self, depth, alpha=float("-inf"), beta=float("inf")):
        self.nodes += 1
        best = float("-inf") if self.game.white_to_move else float("inf")
        
        # If Depth is zero return
        if depth <= 0:
            return self.quiescence(alpha, beta)
        
        # Now generate all legal moves so we can explore them
        moves = self.orderMoves(self.game.generateMoves())
        
        # If its whites turn we will keep updating alpha
        if self.game.white_to_move:
            for move in moves:
                self.game.movePiece(move)
                score = self.miniMax(depth - 1, alpha, beta)
                self.game.undoMove(move)
                best = max(best, score)
                alpha = max(alpha, score)

                if alpha >= beta:
                    break 

            return best
        
        # Blacks turn means we must update beta
        else:
            for move in moves:
                self.game.movePiece(move)
                score = self.miniMax(depth - 1, alpha, beta)
                self.game.undoMove(move)

                best = min(best, score)
                beta = min(beta, score)

                if alpha >= beta:
                    break 

            return best
    
    def orderMoves(self, moves: list[Move]) -> list[Move]:
        scored_moves = []

        for move in moves:
            score = self.scoreMove(move)
            scored_moves.append((score, move))

        scored_moves.sort(key=lambda item: item[0], reverse=True)

        return [move for score, move in scored_moves]

    def orderMovesOld(self, moves = list):
        tactical = []
        quiet = []

        for move in moves:
            moving_piece = self.game.getPiece(move.start_rank, move.start_file)
            captured_piece = self.game.getPiece(move.end_rank, move.end_file)
            if captured_piece or ("pawn" in moving_piece and (move.end_rank == 1 or move.end_rank == 8)):
                tactical.append(move)
            else:
                quiet.append(move)
               

        res = tactical + quiet
        return moves

    def scoreMove(self, move: Move) -> int:
        score = 0
        color = "w" if self.game.white_to_move else "b"

        moving_piece = self.game.getPiece(
            move.start_rank,
            move.start_file,
        )

        captured_piece = self.game.getPiece(
            move.end_rank,
            move.end_file,
        )

        moving_value = abs(self.piece_values[moving_piece])

        # Promotion
        if "pawn" in moving_piece and move.end_rank in (1, 8):
            score += 800
        
        # MVV-LVA capture ordering
        if captured_piece:
            captured_value = abs(self.piece_values[captured_piece])
            score += 10_000 + captured_value * 10 - moving_value

        return score

    def bestMoveAtDepth(self, depth, pref):
        bestMove = None
        moves = self.game.generateMoves()
        orderedMoves = self.orderMoves(moves)

        # Reorder moves for iterative deepening, if we have a preffered move look at it first
        if pref is not None and pref in orderedMoves:
            orderedMoves.remove(pref)
            orderedMoves.insert(0, pref)

        best = float("-inf") if self.game.white_to_move else float("inf")
        maximizing = self.game.white_to_move

        alpha = float("-inf")
        beta = float("inf")

        for move in orderedMoves:
            self.game.movePiece(move)
            score = self.miniMax(depth - 1, alpha, beta)
            self.game.undoMove(move)

            if maximizing:
                if score > best:
                    best = score
                    bestMove = move

                alpha = max(alpha, best)

            else:
                if score < best:
                    best = score
                    bestMove = move

                beta = min(beta, best)
        self.eval = best
        return bestMove

    def findBestMove(self, maxDepth):
        best_move = None

        # Wow! Iterative Deepening!
        for curr in range(1, maxDepth + 1):
            start = time.time()
            best_move = self.bestMoveAtDepth(curr, best_move)
            end = time.time()
            print("Spent " + str(round(end - start, 2)) + "(s) exploring " + str(self.nodes) + " nodes of which " + str(self.qnodes) + " were qnodes. " + str(self.qmax) + " reached max Qdepth. Avg Q Depth is " + str(self.qavg/self.qnodes) + " Base Depth is "+ str(curr) + ".")
            self.nodes = 0
            self.qnodes = 1
            self.qavg = 0

        return best_move

    def quiescence(self, alpha=float("-inf"), beta=float("inf"), qdepth = 0):
        self.nodes += 1
        if qdepth == 1:
            self.qnodes += 1
        if qdepth >= QDEPTHMAX:
            self.qmax += 1
            return self.evaluator.evaluate(self.game)
        # Evaluation if we make no further tactical move.
        stand_pat = self.evaluator.evaluate(self.game)

        if self.game.white_to_move:
            # White is maximizing.
            if stand_pat >= beta:
                return beta

            alpha = max(alpha, stand_pat)

            moves = self.game.generateMoves()
            tactical_moves = [
                move for move in moves
                if self.game.getPiece(move.end_rank, move.end_file) is not None
                or move.promotion is not None
            ]

            tactical_moves = self.orderMoves(tactical_moves)

            for move in tactical_moves:
                self.game.movePiece(move)
                score = self.quiescence(alpha, beta)
                self.qavg += 1
                self.game.undoMove(move)

                if score >= beta:
                    return beta

                alpha = max(alpha, score)

            return alpha

        else:
            # Black is minimizing.
            if stand_pat <= alpha:
                return alpha

            beta = min(beta, stand_pat)

            moves = self.game.generateMoves()
            tactical_moves = [
                move for move in moves
                if self.game.getPiece(move.end_rank, move.end_file) is not None
                or move.promotion is not None
            ]

            tactical_moves = self.orderMoves(tactical_moves)

            for move in tactical_moves:
                self.game.movePiece(move)
                score = self.quiescence(alpha, beta, qdepth + 1)
                self.qavg += 1
                self.game.undoMove(move)

                if score <= alpha:
                    return alpha

                beta = min(beta, score)

            return beta

        

        


    