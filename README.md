# Python Chess Engine

A chess engine built from scratch in Python, featuring custom bitboard-based move generation, position evaluation, iterative deepening, alpha-beta search, transposition tables, quiescence search, and a Pygame interface.

This project started as an attempt to understand how chess engines actually work beneath the surface. Rather than relying on an existing chess library for game logic or search, I implemented the board representation, move generation, evaluation, search algorithms, hashing, and engine testing infrastructure myself.

## Features

### Chess Logic

* Bitboard-based board representation
* Full legal move generation
* Check and checkmate detection
* Castling
* En passant
* Pawn promotion
* Draw detection

  * Repetition
  * Insufficient material
* Move undoing for efficient recursive search
* FEN position loading

### Search

* Minimax search
* Alpha-beta pruning
* Iterative deepening
* Principal Variation Search (PVS)
* Aspiration windows
* Quiescence search
* Search time limits
* Move ordering
* Transposition tables

### Position Evaluation

The evaluation function combines several heuristics, including:

* Material balance
* Piece-square tables
* Piece mobility
* Middlegame/endgame interpolation
* Endgame king positioning and checkmating heuristics

### Zobrist Hashing

Positions are incrementally hashed using Zobrist hashing.

The hash incorporates:

* Piece locations
* Side to move
* Castling rights
* En passant state

These hashes are used as keys for the engine's transposition table, allowing previously analyzed positions to be reused during search.

## Engine Architecture

The project is divided into several major systems:

```text
GameState
│
├── Bitboard position representation
├── Legal move generation
├── Make / undo move
├── Attack detection
├── Draw detection
└── Zobrist position hashing

Evaluator
│
├── Material evaluation
├── Piece-square tables
├── Mobility
└── Endgame heuristics

Bot
│
├── Iterative deepening
├── Alpha-beta search
├── Principal Variation Search
├── Quiescence search
├── Move ordering
├── Aspiration windows
└── Transposition table

Interface
│
├── Pygame chessboard
├── Piece animations
├── Move history
└── Search statistics
```

## Search Process

For each position, the engine progressively searches deeper using iterative deepening.

At each depth:

1. Legal moves are generated.
2. Moves are ordered so promising moves are searched first.
3. Alpha-beta pruning eliminates branches that cannot affect the final result.
4. Principal Variation Search uses narrow search windows for non-principal moves.
5. The transposition table reuses information from positions previously searched.
6. At leaf nodes, quiescence search extends tactical positions involving captures and other forcing moves.
7. The evaluator assigns a score to the resulting quiet position.

The strongest move from the deepest completed iteration is then played.

## Optimization and Testing

A major focus of the project has been measuring whether engine optimizations actually improve playing strength rather than assuming that theoretically better algorithms always produce a stronger engine.

I built a bot-battle testing framework that allows different engine configurations to play large sets of games against one another while independently toggling features such as:

* Principal Variation Search
* Aspiration windows
* Transposition tables
* Move ordering
* Quiescence search
* Evaluation heuristics

The framework records wins, losses, draws, elapsed time, and search behavior.

I also use fixed-depth comparisons to verify that optimizations produce equivalent search scores before measuring their effect on speed or playing strength.

This made it possible to evaluate tradeoffs between search overhead, node reduction, search depth, and actual game performance.

## Development Progression

The engine evolved incrementally:

1. Built a playable chessboard and board representation.
2. Implemented pseudo-legal and legal move generation.
3. Added complete chess rules and position state tracking.
4. Built a material-based minimax engine.
5. Added alpha-beta pruning.
6. Introduced move ordering and positional evaluation.
7. Added quiescence search to reduce the horizon effect.
8. Implemented Zobrist hashing and transposition tables.
9. Added iterative deepening and time-controlled search.
10. Implemented Principal Variation Search and aspiration windows.
11. Built automated bot-vs-bot testing infrastructure.
12. Began profiling and optimizing move generation and search performance.

Each optimization is tested independently to determine whether it improves search efficiency and, more importantly, playing strength.

## Technologies

* Python
* Pygame
* Bitboards
* Zobrist hashing
* Minimax / Alpha-Beta Search
* Principal Variation Search
* Transposition Tables

## What I Learned

Building the engine has required working with concepts across algorithms, data structures, optimization, and software architecture.

Some of the most interesting challenges have included:

* Representing chess positions efficiently using 64-bit integers
* Generating legal moves while handling checks, pins, castling, and en passant
* Designing reversible state updates for recursive search
* Understanding the relationship between move ordering and alpha-beta pruning efficiency
* Avoiding tactical evaluation errors with quiescence search
* Designing effective transposition-table replacement and lookup behavior
* Measuring whether an optimization reduces nodes enough to justify its computational overhead
* Building controlled experiments to compare engine configurations

The project has also reinforced an important lesson in optimization: an algorithm that looks faster theoretically is not necessarily stronger under a real time constraint. Profiling and empirical testing are essential.

## Future Improvements

Potential next steps include:

* Killer-move and history heuristics
* Late Move Reductions
* More efficient sliding-piece move generation
* Improved transposition-table replacement policies
* Better endgame evaluation
* Pawn-structure evaluation
* Opening-book support
* Endgame tablebases
* More extensive engine benchmarking
* UCI protocol support
* Formal Elo testing

## Running the Engine

Clone the repository:

```bash
git clone https://github.com/Arcaeyn/Chess-Engine.git
cd Chess-Engine
```

Install Pygame:

```bash
pip install pygame
```

Then run the main game file:

```bash
python game.py
```

## Repository

[github.com/Arcaeyn/Chess-Engine](https://github.com/Arcaeyn/Chess-Engine)
