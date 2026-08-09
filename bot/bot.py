import random
from gameLogic.board import GameState, Move
from bot.evaluation import Evaluator
from dataclasses import dataclass
import time

QDEPTHMAX = 5
EXACT = 0
LOWER_BOUND = 1
UPPER_BOUND = 2
USE_TT = True
MATE_SCORE = 100_000

# Setting up the transposition table
@dataclass
class TTEntry:
    depth: int
    score: float
    flag: int
    best_move: object | None

class Bot:
    def __init__(self, game : GameState):

        # Statistics
        self.eval = 0
        self.qnodes = 1
        self.qmax = 0
        self.qavg = 0
        self.tt_hits = 0
        self.nodes = 0

        # Feature Switching for Search Fucntion
        self.useTranspositionTable = True
        self.useQuiescence = True
        self.useAlphaBetaPruning = True
        self.useIterativeDeepening = True
        self.useMoveOrdering = True

        # Other importnat stuff
        self.depth = 3
        self.game = game
        self.evaluator = Evaluator(self.game)
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
        self.transposition_table = {}
    
    def playRandom(self):
        moves = self.game.generateMoves()
        if len(moves) > 0:
            return moves[random.randint(0, len(moves) - 1)]
    
    # Mini Max w/ alpha beta pruning
    def miniMax(self, depth, alpha=float("-inf"), beta=float("inf")):
        self.nodes += 1

        original_alpha = alpha
        original_beta = beta
        hash_key = self.game.zobrist_hash

        if (
        self.game.isThreefoldRepetition()
        or self.game.isFiftyMoveDraw()
        or self.game.hasInsufficientMaterial()
    ):
            return 0
        
        # If Depth is zero return
        if depth <= 0:
            return self.quiescence(alpha, beta)
        

        if USE_TT:
            # Let us now check the transpotion table
            entry = self.transposition_table.get(hash_key)
            tt_move = entry.best_move if entry else None

            if entry is not None and entry.depth >= depth:
                self.tt_hits += 1
                if entry.flag == EXACT:
                    return entry.score

                if entry.flag == LOWER_BOUND:
                    alpha = max(alpha, entry.score)

                elif entry.flag == UPPER_BOUND:
                    beta = min(beta, entry.score)

                if alpha >= beta:
                    return entry.score
                
         # Now generate all legal moves so we can explore them
        moves = self.orderMoves(self.game.generateMoves())

        # Gotta Check for checkmate and such
        moving_color = "w" if self.game.white_to_move else "b"

        if not moves:
            if self.game.kingInCheck(moving_color):
                if self.game.white_to_move:
                    return -MATE_SCORE
                else:
                    return MATE_SCORE

            return 0  # stalemate

        if USE_TT:
            # Move TT move to front
            if tt_move is not None:
                for index, move in enumerate(moves):
                    if self.sameMove(move, tt_move):
                        moves.insert(0, moves.pop(index))
                        break

        best_move = None
        # If its whites turn we will keep updating alpha
        if self.game.white_to_move:
            best = float("-inf")
            for move in moves:
                self.game.movePiece(move)
                score = self.miniMax(depth - 1, alpha, beta)
                self.game.undoMove(move)

                if score > best:
                    best = score
                    best_move = move

                alpha = max(alpha, best)

                if alpha >= beta:
                    break 

        # Blacks turn means we must update beta
        else:
            best = float("inf")

            for move in moves:
                self.game.movePiece(move)
                score = self.miniMax(depth - 1, alpha, beta)
                self.game.undoMove(move)

                if score < best:
                    best = score
                    best_move = move

                beta = min(beta, best)

                if alpha >= beta:
                    break
        
        # Determine what kind of value was produced.
        if best <= original_alpha:
            flag = UPPER_BOUND

        elif best >= original_beta:
            flag = LOWER_BOUND

        else:
            flag = EXACT

        new_entry = TTEntry(
            depth=depth,
            score=best,
            flag=flag,
            best_move=best_move,
        )

        old_entry = self.transposition_table.get(hash_key)

        # Do not replace a deeper result with a shallower result.
        if old_entry is None or depth >= old_entry.depth:
            self.transposition_table[hash_key] = new_entry

        return best

    # We want to order moves from roughly best to worst, this will have us examine 
    # captures and promotion first as they are most likely the best moves
    def orderMoves(self, moves: list[Move]) -> list[Move]:
        scored_moves = []

        for move in moves:
            score = self.scoreMove(move)
            scored_moves.append((score, move))

        scored_moves.sort(key=lambda item: item[0], reverse=True)

        return [move for score, move in scored_moves]

    # We need help detemring which moves and which captures are beter, therefore we score moves
    # For example we prefer to capture a queen with a pawn then a pawn with a queen so we distinc for that
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

    # Caluclates the score of a move at a depth, this is needed for out iterative deepening
    def bestMoveAtDepth(self, depth, pref):
        bestMove = None
        moves = self.game.generateMoves()
        if self.useMoveOrdering:
            orderedMoves = self.orderMoves(moves)
        else: 
            orderedMoves = moves

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
            score = self.searchToggle(depth - 1, alpha, beta)
            self.game.undoMove(move)

            if maximizing:
                if score > best:
                    best = score
                    bestMove = move

                if self.useAlphaBetaPruning:
                    alpha = max(alpha, best)

            else:
                if score < best:
                    best = score
                    bestMove = move

                if self.useAlphaBetaPruning:
                    beta = min(beta, best)

        self.eval = best
        return best, bestMove

    # Iterative Deepening
    def findBestMove(self, maxDepth):
        best_move = None

        # Wow! Iterative Deepening!
        for curr in range(1, maxDepth + 1):
            start = time.time()
            score, best_move = self.bestMoveAtDepth(curr, best_move)
            end = time.time()
            print("Spent " + str(round(end - start, 2)) + "(s) exploring " + str(self.nodes) + " nodes of which " + str(self.qnodes) + " were qnodes. " + str(self.qmax) + " reached max Qdepth. Avg Q Depth is " + str(self.qavg/self.qnodes) + " Base Depth is "+ str(curr) + ".")
            print(
 f"TT entries: {len(self.transposition_table)}, "
    f"TT hits: {self.tt_hits}"
)
            self.nodes = 0
            self.tt_hits = 0
            self.qnodes = 1
            self.qmax = 0
            self.qavg = 0

        self.eval = score
        return best_move

    # Quisence search is pretty cool, basically a search extension for moves that are interesting
    # this allows us to explore full capture sequences or promotion sequneces
    # This helps make our eval more accurate so that on turns where black has just captured and white was to recapture 
    # next turn we make sure to account for that, it also allows us to explore the most "interesting" moves to a much deeper depth making our engine stronger
    def quiescence(self, alpha=float("-inf"), beta=float("inf"), qdepth = 0):

        # Update node count
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
                score = self.quiescence(alpha, beta, qdepth + 1)

                # every time we call quisemce we add this 
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

    # Move Comparison
    def sameMove(self, move_a: Move | None, move_b: Move | None) -> bool:
        if move_a is None or move_b is None:
            return False

        return (
            move_a.start_rank == move_b.start_rank
            and move_a.start_file == move_b.start_file
            and move_a.end_rank == move_b.end_rank
            and move_a.end_file == move_b.end_file
            and move_a.promotion == move_b.promotion
            and move_a.is_castle == move_b.is_castle
            and move_a.is_en_passant == move_b.is_en_passant
        )
    

    def searchToggle(self, depth, alpha=float("-inf"), beta=float("inf")):
        # Update Node Count
        self.nodes += 1
        original_alpha = alpha
        original_beta = beta

        # Handle Draws
        if (
                self.game.isThreefoldRepetition()
                or self.game.isFiftyMoveDraw()
                or self.game.hasInsufficientMaterial()
            ):
                    return 0
                
        # If Depth is zero return
        if depth <= 0:
            if self.useQuiescence:
                return self.quiescence(alpha, beta)

            else:
                return self.evaluator.evaluate(self.game)

        # Transpostion Table
        if self.useTranspositionTable:
            hash_key = self.game.zobrist_hash
            entry = self.transposition_table.get(hash_key)
            tt_move = entry.best_move if entry else None

            if entry is not None and entry.depth >= depth:
                self.tt_hits += 1
                if entry.flag == EXACT:
                    return entry.score

                if entry.flag == LOWER_BOUND:
                    alpha = max(alpha, entry.score)

                elif entry.flag == UPPER_BOUND:
                    beta = min(beta, entry.score)

                if alpha >= beta:
                    return entry.score

        # Generate All Legal Moves
        if self.useMoveOrdering:
            moves = self.orderMoves(self.game.generateMoves())

        else:
            moves = self.game.generateMoves()          

        # Check for Checkmate
        moving_color = "w" if self.game.white_to_move else "b"
        
        if not moves:
            if self.game.kingInCheck(moving_color):
                if self.game.white_to_move:
                    return -MATE_SCORE
                else:
                    return MATE_SCORE

            return 0  # stalemate

        if self.useTranspositionTable:
            # Move TT move to front
            if tt_move is not None:
                for index, move in enumerate(moves):
                    if self.sameMove(move, tt_move):
                        moves.insert(0, moves.pop(index))
                        break

        best_move = None

        # If its whites turn we will keep updating alpha
        if self.game.white_to_move:
            best = float("-inf")
            for move in moves:
                self.game.movePiece(move)
                score = self.searchToggle(depth - 1, alpha, beta)
                self.game.undoMove(move)

                if score > best:
                    best = score
                    best_move = move

                if self.useAlphaBetaPruning:
                    alpha = max(alpha, best)

                    if alpha >= beta:
                        break 

        # Otherwise update beta
        else:
            best = float("inf")

            for move in moves:
                self.game.movePiece(move)
                score = self.searchToggle(depth - 1, alpha, beta)
                self.game.undoMove(move)

                if score < best:
                    best = score
                    best_move = move


                if self.useAlphaBetaPruning:
                    beta = min(beta, best)

                    if alpha >= beta:
                        break

        # Determine what kind of value was produced.
        if best <= original_alpha:
            flag = UPPER_BOUND

        elif best >= original_beta:
            flag = LOWER_BOUND

        else:
            flag = EXACT

        # Update Transposition table
        if self.useTranspositionTable:
            new_entry = TTEntry(
                        depth=depth,
                        score=best,
                        flag=flag,
                        best_move=best_move,
                    )
            
            old_entry = self.transposition_table.get(hash_key)

            # Do not replace a deeper result with a shallower result.
            if old_entry is None or depth >= old_entry.depth:
                self.transposition_table[hash_key] = new_entry

        return best


    def findMoveToggle(self, baseDepth, pref=None):
        if self.useIterativeDeepening:
            score, move = self.findBestMove(baseDepth)
            return move


        else:
            return self.bestMoveAtDepth(baseDepth, None)