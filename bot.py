import random
from board import GameState, Move
from evaluation import Evaluator


class Bot:
    def __init__(self, game : GameState):
        self.depth = 3
        self.game = game
        self.nodes = 0
        self.evaluator = Evaluator()
        self.bestscore = 0
        self.eval = 0
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
            return self.evaluator.evaluate(self.game)
        
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
    
    def orderMoves(self, moves = list):
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


    def findBestMove(self, depth):
        bestMove = None
        moves = self.game.generateMoves()
        orderedMoves = self.orderMoves(moves)
        best = float("-inf") if self.game.white_to_move else float("inf")
    
        # Make a move then get that moves score and then if its the best one add it to the list
        for move in orderedMoves:
            self.game.movePiece(move)
            score = self.miniMax(depth - 1, float("-inf"), float("inf"))
            self.game.undoMove(move)
            if score > best and self.game.white_to_move:
                bestMove = move
                best = score


            if score < best and not self.game.white_to_move:
                bestMove = move
                best = score

        self.eval = best
        print(self.nodes)
        self.nodes = 0
        return bestMove




        

        


    