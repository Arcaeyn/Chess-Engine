import pygame
import time
import math
import random

from gameLogic.boardChatGPT import GameState, Move
from bot.bot import Bot


TEST_FENS_EQUAL = [
    "rn1qkbnr/pp2pppp/8/2pp4/P3P3/5PPb/1PPP3P/RNBQKBNR w KQkq - 1 5",
    "rnbqkbnr/pp2p2p/3p4/2p2pp1/8/2P3P1/PP1PPP1P/RNBQKBNR w KQkq - 0 5",
    "rn1qkb1r/ppp1pp1p/3p1np1/2P2b2/1P1P4/8/P3PPPP/RNBQKBNR w KQkq - 1 5",
    "rnbqk1nr/1pppbppp/8/p3p1N1/P7/2N5/1PPPPPPP/R1BQKB1R w KQkq - 4 5",
    "r2qkbnr/pppn1ppp/3pb3/4p3/5P2/1P5P/PBPPP1P1/RN1QKBNR w KQkq - 1 5",
    "r1bqkbnr/ppn1pppp/8/2pp4/P1B1P2P/8/1PPP1PP1/RNBQK1NR w KQkq - 1 5",
    "r1bqkb1r/ppp1p1pp/2np1p1n/8/6Q1/2P1P2P/PP1P1PP1/RNB1KBNR w KQkq - 0 5",
    "rn1qkbnr/pb1p1ppp/1p6/2p1p3/1P4P1/2N5/PBPPPP1P/R2QKBNR w KQkq - 2 5",
    "rnbqkbnr/pp2pppp/3p4/2p3N1/8/P1P5/1P1PPPPP/RNBQKB1R w KQkq - 0 5",
    "rnbqkbnr/1p2p1pp/8/p1pp1p2/1PP5/6P1/P2PPPBP/RNBQK1NR w KQkq a6 0 5",

    "rnbqk1nr/pppp1p1p/8/4p1p1/1b4P1/2P5/PB1PPP1P/RN1QKBNR w KQkq - 0 5",
    "rn1qkbnr/ppp1p1pp/3pbp2/P7/8/2P2N2/1P1PPPPP/RNBQKB1R w KQkq - 1 5",
    "rnbqkbnr/pp3ppp/2p5/3pp3/3P4/3K1P2/PPP1P1PP/RNBQ1BNR w kq - 0 5",
    "rn1qkbnr/pppb2pp/8/3ppp2/2P2P2/1P6/P2PP1PP/RNBQKBNR w KQkq e6 0 5",
    "rnbq2nr/pppp1kpp/3b1p2/4p3/BP2P3/8/P1PP1PPP/RNBQK1NR w KQ - 4 5",
    "r1bqkbnr/pppp1ppp/n3p3/8/N7/P4P2/1PPPP1PP/R1BQKBNR w KQkq - 0 5",
    "rn1qkbnr/p1p1p1pp/1p1pb3/5pN1/3P4/2P5/PP2PPPP/RNBQKB1R w KQkq - 2 5",
    "rnbqkbnr/pp2pp2/2pp3p/6p1/4P3/2P3N1/PP1P1PPP/RNBQKB1R w KQkq g6 0 5",
    "rn1qkbnr/1p2pppp/p2p4/2p2b2/4PP2/2N5/PPPP2PP/R1BQKBNR w KQkq - 1 5",
    "rnbqk1nr/1ppp1pp1/p7/2b1p2p/2P1P2P/5N2/PP1P1PP1/RNBQKB1R w KQkq - 0 5",

    "r1bqkbnr/ppp2ppp/8/3pp3/1nP2P2/N7/PP1PP1PP/R1BQKBNR w KQkq - 1 5",
    "r1bqk1nr/ppppppbp/8/4n1p1/5PP1/4P3/PPPP3P/RNBQKBNR w KQkq - 1 5",
    "rnbqkb1r/pp1pp1pp/7n/2p2p2/8/P1P2P2/1P1PPKPP/RNBQ1BNR w kq - 2 5",
    "rnbqk1nr/p1pp1ppp/1p6/4p3/8/b1P2PPP/PP1PP3/RNBQKBNR w KQkq - 1 5",
    "rnbqkb1r/pp1pp1pp/8/2p2p1P/6n1/2N2P2/PPPPP1P1/R1BQKBNR w KQkq - 1 5",
    "r1bqkb1r/pppn1ppp/3p1n2/4p3/3P3P/N1P5/PP2PPP1/R1BQKBNR w KQkq e6 0 5",
    "rn1qkb1r/1pp1pppp/B6n/3p4/7N/4P2b/PPPP1PPP/RNBQK2R w KQkq - 1 5",
    "rn1qkb1r/pp2pppp/7n/2Pp4/6b1/B2P4/P1P1PPPP/RN1QKBNR w KQkq - 1 5",
    "rnbqk1nr/p1pp1pp1/7p/1p2p1N1/4PP2/b7/PPPP2PP/RNBQKB1R w KQkq - 2 5",
    "r1bqkbnr/pp1ppp1p/n7/2p5/3NP1p1/2P5/PP1P1PPP/RNBQKB1R w KQkq - 1 5",

    "r1bqkbnr/2ppppp1/np6/p6p/3PPB2/2N5/PPP2PPP/R2QKBNR w KQkq - 0 6",
    "r2qkbnr/ppp2pp1/2np3p/4p1N1/6b1/P1P3P1/1P1PPP1P/RNBQKB1R w KQkq e6 0 6",
    "r1bqkbnr/pp1p2pp/8/2pPpp2/1n2P3/6P1/PPP1BP1P/RNBQK1NR w KQkq c6 0 6",
    "r1bqkb1r/pppppppp/n7/2P4n/8/3P4/PP2PPP1/RNBQKBNR w KQkq - 1 6",
    "r1bqkbnr/pp2p1p1/n1p4p/3p1p2/3P4/1P3P2/PBP1P1PP/RN1QKBNR w KQkq d6 0 6",
    "r2qkbnr/ppp3pp/n4p2/3ppb2/4PB2/3P2P1/PPP2P1P/RN1QKBNR w KQkq - 2 6",
    "r1bqkbnr/pp4pp/n1ppp3/1N3p2/7P/5N2/PPPPPPP1/1RBQKB1R w Kkq - 0 6",
    "rnbqkb1r/pp1p1ppp/8/4p3/2pPn3/N1P5/PP2PPPP/R1BQKBNR w KQkq - 2 6",
    "r1bqkbnr/pp1p2pp/n3p3/2p5/5pP1/PP5P/2PPPPB1/RNBQK1NR w KQkq - 0 6",
    "rnbqkb1r/pp1p3p/6pn/2p1pp2/4P2P/2P5/PP1P1PP1/RNBQKBNR w KQkq e6 0 6",

    "r1b1kbnr/p1qpp1pp/npp2p2/8/4P2P/2P5/PP1PBPP1/RNBQK1NR w KQkq - 0 6",
    "r2qkbnr/p1ppp1pp/1pn5/5p2/1PP3P1/8/P2PbP1P/RNBQKBNR w KQkq - 1 6",
    "r1bqkbnr/1p1ppp1p/p5p1/2p1n3/8/2NP1NP1/PPPKPP1P/R1BQ1B1R w kq - 0 6",
    "rnbqk1nr/1ppp1p2/6Pp/p3p3/8/b1P2P2/PP1PP1P1/RNBQKBNR w KQkq - 1 6",
    "rn1qkbnr/ppp3pp/4pp2/5b2/2P1p3/4P2P/PP1P1PP1/R1BQKBNR w KQkq - 0 6",
    "r1bqkb1r/1pppp1pp/n4p2/p7/6P1/6P1/PPPPP2P/RNBQKBNR w KQkq - 0 6",
    "r1bqk1nr/ppppppbp/6p1/4n3/2P5/N3PP2/PP1PK1PP/R1BQ1BNR w kq - 1 6",
    "r1bqkbnr/p1p1p1pp/1p1p4/3N1p2/1n3P2/3P3N/PPP1P1PP/R1BQKB1R w KQkq - 3 6",
    "r1bqkbnr/pp4pp/n1pppp2/8/4P3/1PP3P1/PB1P1P1P/RN1QKBNR w KQkq - 2 6",
    "rnbqk1nr/1ppp1ppp/7B/4p3/p2P3P/b1P2N2/PP2PPP1/RN1QKB1R w KQkq - 0 6",
]

TEST_FENS = [
    # White: Queen vs King
    "8/8/8/8/4k3/8/8/K6Q w - - 0 1",
    "8/8/2k5/8/8/8/6Q1/K7 w - - 0 1",
    "8/8/8/5k2/8/2Q5/8/K7 w - - 0 1",
    "8/8/8/8/2k5/8/Q7/6K1 w - - 0 1",
    "8/8/6k1/8/8/8/3Q4/K7 w - - 0 1",

    # Black: Queen vs King
    "k6q/8/8/4K3/8/8/8/8 b - - 0 1",
    "7k/1q6/8/8/3K4/8/8/8 b - - 0 1",
    "7k/8/5q2/8/2K5/8/8/8 b - - 0 1",
    "1q5k/8/8/4K3/8/8/8/8 b - - 0 1",
    "7k/3q4/8/8/8/2K5/8/8 b - - 0 1",

    # White: Rook vs King
    "8/8/8/8/4k3/8/8/K6R w - - 0 1",
    "8/8/2k5/8/8/8/6R1/K7 w - - 0 1",
    "8/8/8/5k2/8/2R5/8/K7 w - - 0 1",
    "8/8/8/8/2k5/8/R7/6K1 w - - 0 1",
    "8/8/6k1/8/8/8/3R4/K7 w - - 0 1",

    # Black: Rook vs King
    "k6r/8/8/4K3/8/8/8/8 b - - 0 1",
    "7k/1r6/8/8/3K4/8/8/8 b - - 0 1",
    "7k/8/5r2/8/2K5/8/8/8 b - - 0 1",
    "1r5k/8/8/4K3/8/8/8/8 b - - 0 1",
    "7k/3r4/8/8/8/2K5/8/8 b - - 0 1",

    # White: Queen + Pawn vs King
    "8/8/8/8/4k3/8/P7/K6Q w - - 0 1",
    "8/8/2k5/8/8/8/5PQ1/K7 w - - 0 1",
    "8/8/8/5k2/8/2Q5/P7/K7 w - - 0 1",

    # Black: Queen + Pawn vs King
    "k6q/p7/8/4K3/8/8/8/8 b - - 0 1",
    "7k/1q3p2/8/8/3K4/8/8/8 b - - 0 1",
    "7k/p7/5q2/8/2K5/8/8/8 b - - 0 1",

    # White: Rook + Pawn vs King
    "8/8/8/8/4k3/8/P7/K6R w - - 0 1",
    "8/8/2k5/8/8/8/5PR1/K7 w - - 0 1",

    # Black: Rook + Pawn vs King
    "k6r/p7/8/4K3/8/8/8/8 b - - 0 1",
    "7k/1r3p2/8/8/3K4/8/8/8 b - - 0 1",
]
game_state = GameState()
bot1 = Bot(game_state)
bot1.displayStats = False

bot2 = Bot(game_state)
bot2.displayStats = False
bot2.evaluator.useMopUp = False

totalgames = len(TEST_FENS) * 2

def formatTime(seconds):
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes:02d}m {seconds:02d}s"

    return f"{minutes}m {seconds:02d}s"


def displayProgress(
    completed_games,
    total_games,
    current_ply,
    bot1_wins,
    bot2_wins,
    draws,
    start_time,
):
    elapsed = time.perf_counter() - start_time

    if completed_games > 0:
        average_game_time = elapsed / completed_games
        remaining_games = total_games - completed_games
        estimated_remaining = average_game_time * remaining_games
        eta_text = formatTime(estimated_remaining)
    else:
        eta_text = "calculating..."

    progress = completed_games / total_games
    bar_length = 30
    filled = int(progress * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)

    print(
        f"\r[{bar}] "
        f"{completed_games}/{total_games} games | "
        f"Current ply: {current_ply:3d} | "
        f"Bot 1: {bot1_wins} | "
        f"Bot 2: {bot2_wins} | "
        f"Draws: {draws} | "
        f"Elapsed: {formatTime(elapsed)} | "
        f"ETA: {eta_text}",
        end="",
        flush=True,
    )


bot1_wins = 0
bot2_wins = 0
draws = 0
completed_games = 0
battle_start = time.perf_counter()


def updateProgress(ply):
    displayProgress(
        completed_games=completed_games,
        total_games=totalgames,
        current_ply=ply,
        bot1_wins=bot1_wins,
        bot2_wins=bot2_wins,
        draws=draws,
        start_time=battle_start,
    )

def playGame(
    game_state: GameState,
    white_bot: Bot,
    black_bot: Bot,
    depth1: int,
    depth2: int,
    time1: float,
    time2: float,
    progress_callback=None,
):
    MAX_PLIES = 300

    for ply in range(MAX_PLIES):
        if progress_callback is not None:
            progress_callback(ply)

        # Side to move has been checkmated.
        if game_state.isCheckmate():
            if game_state.white_to_move:
                return 0, 1
            else:
                return 1, 0

        if game_state.isDraw():
            return 0, 0

        if game_state.white_to_move:
            move = white_bot.findMoveToggle(
                baseDepth=depth1,
                maxTime=time1,
            )
        else:
            move = black_bot.findMoveToggle(
                baseDepth=depth2,
                maxTime=time2,
            )

        if move is None:
            return 0, 0

        game_state.movePiece(move)

    return 0, 0

for index, fen in enumerate(TEST_FENS):
    game_state.loadFen(fen)

    bot1.transposition_table.clear()
    bot1.deadline = None

    original_hash = game_state.zobrist_hash
    original_position = game_state.positionKey()

    score1, move1 = bot1.bestMoveAtDepth(
        depth=2,
        pref=None,
    )

    assert game_state.zobrist_hash == original_hash
    assert game_state.positionKey() == original_position

    bot2.deadline = None

    score2, move2 = bot2.bestMoveAtDepth(
        depth=2,
        pref=None,
    )

    assert game_state.zobrist_hash == original_hash
    assert game_state.positionKey() == original_position

    if score1 != score2:
        print("\nMISMATCH")
        print("Position:", index + 1)
        print("FEN:", fen)
        print("Bot 1 score:", score1)
        print("Bot 2 score:", score2)
        print("Bot 1 move:", move1)
        print("Bot 2 move:", move2)
        break
else:
    print("All fixed-depth scores matched.")

for idx, fen in enumerate(TEST_FENS):
    # Game 1: Bot 1 is White
    bot1.transposition_table.clear()
    bot2.transposition_table.clear()
    game_state.loadFen(fen)

    white_win, black_win = playGame(
        game_state,
        bot1,
        bot2,
        5,
        5,
        0.1,
        0.1,
        progress_callback=updateProgress,
    )

    bot1_wins += white_win
    bot2_wins += black_win

    if white_win == 0 and black_win == 0:
        draws += 1

    completed_games += 1
    updateProgress(0)

    # Game 2: Bot 2 is White
    bot1.transposition_table.clear()
    bot2.transposition_table.clear()
    game_state.loadFen(fen)

    white_win, black_win = playGame(
        game_state,
        bot2,
        bot1,
        5,
        5,
        0.1,
        0.1,
        progress_callback=updateProgress,
    )

    bot2_wins += white_win
    bot1_wins += black_win

    if white_win == 0 and black_win == 0:
        draws += 1

    completed_games += 1
    updateProgress(0)


total_time = time.perf_counter() - battle_start

print("\n")
print("Battle complete!")
print("Bot 1 wins:", bot1_wins)
print("Bot 2 wins:", bot2_wins)
print("Draws:", draws)
print("Total time:", formatTime(total_time))