import pygame
import time
import math
import random

from gameLogic.board import GameState, Move
from bot.bot import Bot


TEST_FENS = [
    # Italian
    "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 1 5",

    # Ruy Lopez
    "r1bqkb1r/1ppp1ppp/p1n2n2/4p3/B3P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 2 5",

    # Scotch
    "r1bqkb1r/pppp1ppp/2n2n2/8/3NP3/8/PPP2PPP/RNBQKB1R w KQkq - 1 5",

    # Four Knights
    "r1bqk2r/pppp1ppp/2n2n2/1B2p3/1b2P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 6 5",

    # Queen's Gambit Declined
    "rnbqk2r/ppp1bppp/4pn2/3p2B1/2PP4/2N5/PP2PPPP/R2QKBNR w KQkq - 4 5",

    # Slav
    "rnbqkb1r/pp2pppp/2p2n2/8/2pP4/2N2N2/PP2PPPP/R1BQKB1R w KQkq - 0 5",

    # Caro-Kann Exchange
    "r1bqkbnr/pp2pppp/2n5/3p4/3P4/3B4/PPP2PPP/RNBQK1NR w KQkq - 2 5",

    # French Exchange
    "rnbqkb1r/ppp2ppp/5n2/3p4/3P4/5N2/PPP2PPP/RNBQKB1R w KQkq - 2 5",

    # English
    "rnbqkb1r/ppp2ppp/8/3np3/8/2N3P1/PP1PPP1P/R1BQKBNR w KQkq - 0 5",

    # Réti
    "rnbqk2r/ppp1bppp/4pn2/3p4/8/5NP1/PPPPPPBP/RNBQ1RK1 w kq - 2 5",

    # Open Sicilian
    "rnbqkb1r/pp2pppp/3p1n2/8/3NP3/8/PPP2PPP/RNBQKB1R w KQkq - 1 5",

    # Alapin Sicilian
    "rnbqkb1r/pp1ppppp/8/3nP3/3p4/2P5/PP3PPP/RNBQKBNR w KQkq - 0 5",

    # Scandinavian
    "rnbqkb1r/ppp1pppp/5n2/8/3P4/2N5/PPP2PPP/R1BQKBNR w KQkq - 1 5",

    # King's Indian
    "rnbqk2r/ppp1ppbp/3p1np1/8/2PPP3/2N5/PP3PPP/R1BQKBNR w KQkq - 0 5",

    # Nimzo-Indian
    "rnbq1rk1/pppp1ppp/4pn2/8/1bPP4/2N1P3/PP3PPP/R1BQKBNR w KQ - 1 5",
]

game_state = GameState()
bot1 = Bot(game_state)
bot1.useTranspositionTable = True

bot2 = Bot(game_state)
bot2.useQuiescence = False

totalgames = len(TEST_FENS) * 2

def playGame(
    game_state: GameState,
    bot1: Bot,
    bot2: Bot,
    depth1: int,
    depth2: int,
):
    MAX_PLIES = 300

    for ply in range(MAX_PLIES):
        # Side to move has been checkmated.
        if game_state.isCheckmate():
            if game_state.white_to_move:
                return 0, 1  # Black/bot2 wins
            else:
                return 1, 0  # White/bot1 wins

        if game_state.isDraw():
            return 0, 0

        if game_state.white_to_move:
            move = bot1.findMoveToggle(depth1)
        else:
            move = bot2.findMoveToggle(depth2)

        # Safety fallback for stalemate or an engine bug.
        if move is None:
            return 0, 0

        game_state.movePiece(move)

    # Adjudicate exceptionally long games as draws.
    return 0, 0

bot1_wins = 0
bot2_wins = 0


for idx in range(0, len(TEST_FENS)):
    fen = TEST_FENS[idx]

    # Bot 1 as white
    bot1.transposition_table.clear()
    bot2.transposition_table.clear()
    game_state.loadFen(fen)
    one, two = playGame(game_state, bot1, bot2, 3, 3)
    bot1_wins += one
    bot2_wins += two

    # Bot 2 as white
    bot1.transposition_table.clear()
    bot2.transposition_table.clear()
    game_state.loadFen(fen)
    one, two = playGame(game_state, bot2, bot1, 3, 3)
    bot2_wins += one
    bot1_wins += two


print("Bot 1 wins: " + str(bot1_wins))
print("Bot 2 wins: " + str(bot2_wins))
print("Draws: " + str(totalgames - bot1_wins - bot2_wins))

