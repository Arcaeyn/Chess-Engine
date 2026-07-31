class Board:
    def __init__(self):
        # White pieces
        self.white_pawns   = 0x000000000000FF00
        self.white_rooks   = 0x0000000000000081
        self.white_knights = 0x0000000000000042
        self.white_bishops = 0x0000000000000024
        self.white_queens  = 0x0000000000000008
        self.white_kings   = 0x0000000000000010

        # Black pieces
        self.black_pawns   = 0x00FF000000000000
        self.black_rooks   = 0x8100000000000000
        self.black_knights = 0x4200000000000000
        self.black_bishops = 0x2400000000000000
        self.black_queens  = 0x0800000000000000
        self.black_kings   = 0x1000000000000000

        self.piece_names = [
            "white_pawns", "black_pawns",
            "white_rooks", "black_rooks",
            "white_knights", "black_knights",
            "white_bishops", "black_bishops",
            "white_queens", "black_queens",
            "white_kings", "black_kings"
        ]

    def resetBoard(self):
         # White pieces
        self.white_pawns   = 0x000000000000FF00
        self.white_rooks   = 0x0000000000000081
        self.white_knights = 0x0000000000000042
        self.white_bishops = 0x0000000000000024
        self.white_queens  = 0x0000000000000008
        self.white_kings   = 0x0000000000000010

        # Black pieces
        self.black_pawns   = 0x00FF000000000000
        self.black_rooks   = 0x8100000000000000
        self.black_knights = 0x4200000000000000
        self.black_bishops = 0x2400000000000000
        self.black_queens  = 0x0800000000000000
        self.black_kings   = 0x1000000000000000

    def pieceColor(self, rank, file):
        whiteMask = self.white_rooks | self.white_knights | self.white_bishops | self.white_queens | self.white_kings | self.white_pawns
        blackMask = self.black_rooks | self.black_knights | self.black_bishops | self.black_queens | self.black_kings | self.black_pawns
        pieceMask = 1 << ((rank - 1) * 8 + (file - 1))
        if pieceMask & whiteMask:
            return "w"

        if pieceMask & blackMask:
            return "b"

        return False
    
    def movePiece(self, rank, file, destRank, destFile):
        selectedMask = 1 << ((rank - 1) * 8 + (file - 1))
        destMask = 1 << ((destRank - 1) * 8 + (destFile - 1))

        # Remove any Piece in destination
        for piece_name in self.piece_names:
            piece = getattr(self, piece_name)
            if piece & destMask:
                piece ^= destMask
                setattr(self, piece_name, piece)

        # Make Move
        for piece_name in self.piece_names:
            piece = getattr(self, piece_name)
            if piece & selectedMask:
                piece ^= selectedMask
                piece |= destMask
                setattr(self, piece_name, piece)
                return True
            
        return False

    def getKnightMoves(self, rank, file, color="w"):
        KNIGHT_MOVES = [(2, 1), (2, -1),
                        (-2, 1), (-2, -1),
                        (1, 2), (1, -2),
                        (-1, 2), (-1, -2)]

        knightMoves = 0
        for move in KNIGHT_MOVES:
            if rank + move[0] > 0 and rank + move[0] < 9 and file + move[1] > 0 and file + move[1] < 9 and self.pieceColor(rank + move[0], file + move[1]) != color:
                print(self.pieceColor(rank + move[0], file + move[1]))
                moveMask = 1 << (((rank + move[0]) - 1) * 8 + ((file + move[1]) - 1))
                knightMoves |= moveMask

        return knightMoves

    def getPawnMoves(self, rank, file, color="w"):
        # Black pawns go down White Pawns go Up also check file
        dir = 1
        pawnMoves = 0
        if color == "b":
            if rank == 7:
                moves = [1, 2]
            else:
                moves = [1]
            dir = -1

        else:
            if rank == 2:
                moves = [1, 2]

            else:
                moves = [1]

        # Get file
        for move in moves:
            if rank + move < 9 and rank + move > 0:
                moveMask = 1 << (((rank + move) - 1) * 8 + file -1 )
                pawnMoves |= moveMask

        return pawnMoves

    def getRookMoves(self, rank, file, color="w"):
        return

        
            
        
        
                        





        
        


