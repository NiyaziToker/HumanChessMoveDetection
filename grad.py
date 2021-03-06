#!/usr/bin/env pypy
# -*- coding: utf-8 -*-

from __future__ import print_function
import re, sys, time
from itertools import count
from collections import OrderedDict, namedtuple
import numpy as np
import cv2
import time
from matplotlib import pyplot as plt
import serial
ser = serial.Serial('/dev/ttyUSB0')
w=480
h=480
harf = ['a','b','c','d','e','f','g','h']
numara = [8, 7, 6, 5, 4, 3, 2, 1]

###############################################################################
# Piece-Square tables. Tune these to change sunfish's behaviour
###############################################################################

piece = { 'P': 100, 'N': 280, 'B': 320, 'R': 479, 'Q': 929, 'K': 60000 }
pst = {
    'P': (   0,   0,   0,   0,   0,   0,   0,   0,
            78,  83,  86,  73, 102,  82,  85,  90,
             7,  29,  21,  44,  40,  31,  44,   7,
           -17,  16,  -2,  15,  14,   0,  15, -13,
           -26,   3,  10,   9,   6,   1,   0, -23,
           -22,   9,   5, -11, -10,  -2,   3, -19,
           -31,   8,  -7, -37, -36, -14,   3, -31,
             0,   0,   0,   0,   0,   0,   0,   0),
    'N': ( -66, -53, -75, -75, -10, -55, -58, -70,
            -3,  -6, 100, -36,   4,  62,  -4, -14,
            10,  67,   1,  74,  73,  27,  62,  -2,
            24,  24,  45,  37,  33,  41,  25,  17,
            -1,   5,  31,  21,  22,  35,   2,   0,
           -18,  10,  13,  22,  18,  15,  11, -14,
           -23, -15,   2,   0,   2,   0, -23, -20,
           -74, -23, -26, -24, -19, -35, -22, -69),
    'B': ( -59, -78, -82, -76, -23,-107, -37, -50,
           -11,  20,  35, -42, -39,  31,   2, -22,
            -9,  39, -32,  41,  52, -10,  28, -14,
            25,  17,  20,  34,  26,  25,  15,  10,
            13,  10,  17,  23,  17,  16,   0,   7,
            14,  25,  24,  15,   8,  25,  20,  15,
            19,  20,  11,   6,   7,   6,  20,  16,
            -7,   2, -15, -12, -14, -15, -10, -10),
    'R': (  35,  29,  33,   4,  37,  33,  56,  50,
            55,  29,  56,  67,  55,  62,  34,  60,
            19,  35,  28,  33,  45,  27,  25,  15,
             0,   5,  16,  13,  18,  -4,  -9,  -6,
           -28, -35, -16, -21, -13, -29, -46, -30,
           -42, -28, -42, -25, -25, -35, -26, -46,
           -53, -38, -31, -26, -29, -43, -44, -53,
           -30, -24, -18,   5,  -2, -18, -31, -32),
    'Q': (   6,   1,  -8,-104,  69,  24,  88,  26,
            14,  32,  60, -10,  20,  76,  57,  24,
            -2,  43,  32,  60,  72,  63,  43,   2,
             1, -16,  22,  17,  25,  20, -13,  -6,
           -14, -15,  -2,  -5,  -1, -10, -20, -22,
           -30,  -6, -13, -11, -16, -11, -16, -27,
           -36, -18,   0, -19, -15, -15, -21, -38,
           -39, -30, -31, -13, -31, -36, -34, -42),
    'K': (   4,  54,  47, -99, -99,  60,  83, -62,
           -32,  10,  55,  56,  56,  55,  10,   3,
           -62,  12, -57,  44, -67,  28,  37, -31,
           -55,  50,  11,  -4, -19,  13,   0, -49,
           -55, -43, -52, -28, -51, -47,  -8, -50,
           -47, -42, -43, -79, -64, -32, -29, -32,
            -4,   3, -14, -50, -57, -18,  13,   4,
            17,  30,  -3, -14,   6,  -1,  40,  18),
}
# Pad tables and join piece and pst dictionaries
for k, table in pst.items():
    padrow = lambda row: (0,) + tuple(x+piece[k] for x in row) + (0,)
    pst[k] = sum((padrow(table[i*8:i*8+8]) for i in range(8)), ())
    pst[k] = (0,)*20 + pst[k] + (0,)*20

###############################################################################
# Global constants
###############################################################################

# Our board is represented as a 120 character string. The padding allows for
# fast detection of moves that don't stay within the board.
A1, H1, A8, H8 = 91, 98, 21, 28
initial = (
    '         \n'  #   0 -  9
    '         \n'  #  10 - 19
    ' rnbqkbnr\n'  #  20 - 29
    ' pppppppp\n'  #  30 - 39
    ' ........\n'  #  40 - 49
    ' ........\n'  #  50 - 59
    ' ........\n'  #  60 - 69
    ' ........\n'  #  70 - 79
    ' PPPPPPPP\n'  #  80 - 89
    ' RNBQKBNR\n'  #  90 - 99
    '         \n'  # 100 -109
    '         \n'  # 110 -119
)

# Lists of possible moves for each piece type.
N, E, S, W = -10, 1, 10, -1
directions = {
    'P': (N, N+N, N+W, N+E),
    'N': (N+N+E, E+N+E, E+S+E, S+S+E, S+S+W, W+S+W, W+N+W, N+N+W),
    'B': (N+E, S+E, S+W, N+W),
    'R': (N, E, S, W),
    'Q': (N, E, S, W, N+E, S+E, S+W, N+W),
    'K': (N, E, S, W, N+E, S+E, S+W, N+W)
}

# Mate value must be greater than 8*queen + 2*(rook+knight+bishop)
# King value is set to twice this value such that if the opponent is
# 8 queens up, but we got the king, we still exceed MATE_VALUE.
# When a MATE is detected, we'll set the score to MATE_UPPER - plies to get there
# E.g. Mate in 3 will be MATE_UPPER - 6
MATE_LOWER = piece['K'] - 10*piece['Q']
MATE_UPPER = piece['K'] + 10*piece['Q']

# The table size is the maximum number of elements in the transposition table.
TABLE_SIZE = 1e8

# Constants for tuning search
QS_LIMIT = 150
EVAL_ROUGHNESS = 20


###############################################################################
# Chess logic
###############################################################################

class Position(namedtuple('Position', 'board score wc bc ep kp')):
    """ A state of a chess game
    board -- a 120 char representation of the board
    score -- the board evaluation
    wc -- the castling rights, [west/queen side, east/king side]
    bc -- the opponent castling rights, [west/king side, east/queen side]
    ep - the en passant square
    kp - the king passant square
    """

    def gen_moves(self):
        # For each of our pieces, iterate through each possible 'ray' of moves,
        # as defined in the 'directions' map. The rays are broken e.g. by
        # captures or immediately in case of pieces such as knights.
        for i, p in enumerate(self.board):
            if not p.isupper(): continue
            for d in directions[p]:
                for j in count(i+d, d):
                    q = self.board[j]
                    # Stay inside the board, and off friendly pieces
                    if q.isspace() or q.isupper(): break
                    # Pawn move, double move and capture
                    if p == 'P' and d in (N, N+N) and q != '.': break
                    if p == 'P' and d == N+N and (i < A1+N or self.board[i+N] != '.'): break
                    if p == 'P' and d in (N+W, N+E) and q == '.' and j not in (self.ep, self.kp): break
                    # Move it
                    yield (i, j)
                    # Stop crawlers from sliding, and sliding after captures
                    if p in 'PNK' or q.islower(): break
                    # Castling, by sliding the rook next to the king
                    if i == A1 and self.board[j+E] == 'K' and self.wc[0]: yield (j+E, j+W)
                    if i == H1 and self.board[j+W] == 'K' and self.wc[1]: yield (j+W, j+E)

    def rotate(self):
        ''' Rotates the board, preserving enpassant '''
        return Position(
            self.board[::-1].swapcase(), -self.score, self.bc, self.wc,
            119-self.ep if self.ep else 0,
            119-self.kp if self.kp else 0)

    def nullmove(self):
        ''' Like rotate, but clears ep and kp '''
        return Position(
            self.board[::-1].swapcase(), -self.score,
            self.bc, self.wc, 0, 0)

    def move(self, move):
        i, j = move
        p, q = self.board[i], self.board[j]
        put = lambda board, i, p: board[:i] + p + board[i+1:]
        # Copy variables and reset ep and kp
        board = self.board
        wc, bc, ep, kp = self.wc, self.bc, 0, 0
        score = self.score + self.value(move)
        # Actual move
        board = put(board, j, board[i])
        board = put(board, i, '.')
        # Castling rights, we move the rook or capture the opponent's
        if i == A1: wc = (False, wc[1])
        if i == H1: wc = (wc[0], False)
        if j == A8: bc = (bc[0], False)
        if j == H8: bc = (False, bc[1])
        # Castling
        if p == 'K':
            wc = (False, False)
            if abs(j-i) == 2:
                kp = (i+j)//2
                board = put(board, A1 if j < i else H1, '.')
                board = put(board, kp, 'R')
        # Pawn promotion, double move and en passant capture
        if p == 'P':
            if A8 <= j <= H8:
                board = put(board, j, 'Q')
            if j - i == 2*N:
                ep = i + N
            if j - i in (N+W, N+E) and q == '.':
                board = put(board, j+S, '.')
        # We rotate the returned position, so it's ready for the next player
        return Position(board, score, wc, bc, ep, kp).rotate()

    def value(self, move):
        i, j = move
        p, q = self.board[i], self.board[j]
        # Actual move
        score = pst[p][j] - pst[p][i]
        # Capture
        if q.islower():
            score += pst[q.upper()][119-j]
        # Castling check detection
        if abs(j-self.kp) < 2:
            score += pst['K'][119-j]
        # Castling
        if p == 'K' and abs(i-j) == 2:
            score += pst['R'][(i+j)//2]
            score -= pst['R'][A1 if j < i else H1]
        # Special pawn stuff
        if p == 'P':
            if A8 <= j <= H8:
                score += pst['Q'][j] - pst['P'][j]
            if j == self.ep:
                score += pst['P'][119-(j+S)]
        return score

###############################################################################
# Search logic
###############################################################################

# lower <= s(pos) <= upper
Entry = namedtuple('Entry', 'lower upper')

# The normal OrderedDict doesn't update the position of a key in the list,
# when the value is changed.
class LRUCache:
    '''Store items in the order the keys were last added'''
    def __init__(self, size):
        self.od = OrderedDict()
        self.size = size

    def get(self, key, default=None):
        try: self.od.move_to_end(key)
        except KeyError: return default
        return self.od[key]

    def __setitem__(self, key, value):
        try: del self.od[key]
        except KeyError:
            if len(self.od) == self.size:
                self.od.popitem(last=False)
        self.od[key] = value

class Searcher:
    def __init__(self):
        self.tp_score = LRUCache(TABLE_SIZE)
        self.tp_move = LRUCache(TABLE_SIZE)
        self.nodes = 0

    def bound(self, pos, gamma, depth, root=True):
        """ returns r where
                s(pos) <= r < gamma    if gamma > s(pos)
                gamma <= r <= s(pos)   if gamma <= s(pos)"""
        self.nodes += 1

        # Depth <= 0 is QSearch. Here any position is searched as deeply as is needed for calmness, and so there is no reason to keep different depths in the transposition table.
        depth = max(depth, 0)

        # Sunfish is a king-capture engine, so we should always check if we
        # still have a king. Notice since this is the only termination check,
        # the remaining code has to be comfortable with being mated, stalemated
        # or able to capture the opponent king.
        if pos.score <= -MATE_LOWER:
            return -MATE_UPPER

        # Look in the table if we have already searched this position before.
        # We also need to be sure, that the stored search was over the same
        # nodes as the current search.
        entry = self.tp_score.get((pos, depth, root), Entry(-MATE_UPPER, MATE_UPPER))
        if entry.lower >= gamma and (not root or self.tp_move.get(pos) is not None):
            return entry.lower
        if entry.upper < gamma:
            return entry.upper

        # Here extensions may be added
        # Such as 'if in_check: depth += 1'

        # Generator of moves to search in order.
        # This allows us to define the moves, but only calculate them if needed.
        def moves():
            # First try not moving at all
            if depth > 0 and not root and any(c in pos.board for c in 'RBNQ'):
                yield None, -self.bound(pos.nullmove(), 1-gamma, depth-3, root=False)
            # For QSearch we have a different kind of null-move
            if depth == 0:
                yield None, pos.score
            # Then killer move. We search it twice, but the tp will fix things for us. Note, we don't have to check for legality, since we've already done it before. Also note that in QS the killer must be a capture, otherwise we will be non deterministic.
            killer = self.tp_move.get(pos)
            if killer and (depth > 0 or pos.value(killer) >= QS_LIMIT):
                yield killer, -self.bound(pos.move(killer), 1-gamma, depth-1, root=False)
            # Then all the other moves
            for move in sorted(pos.gen_moves(), key=pos.value, reverse=True):
                if depth > 0 or pos.value(move) >= QS_LIMIT:
                    yield move, -self.bound(pos.move(move), 1-gamma, depth-1, root=False)

        # Run through the moves, shortcutting when possible
        best = -MATE_UPPER
        for move, score in moves():
            best = max(best, score)
            if best >= gamma:
                # Save the move for pv construction and killer heuristic
                self.tp_move[pos] = move
                break

        # Stalemate checking is a bit tricky: Say we failed low, because
        # we can't (legally) move and so the (real) score is -infty.
        # At the next depth we are allowed to just return r, -infty <= r < gamma,
        # which is normally fine.
        # However, what if gamma = -10 and we don't have any legal moves?
        # Then the score is actaully a draw and we should fail high!
        # Thus, if best < gamma and best < 0 we need to double check what we are doing.
        # This doesn't prevent sunfish from making a move that results in stalemate,
        # but only if depth == 1, so that's probably fair enough.
        # (Btw, at depth 1 we can also mate without realizing.)
        if best < gamma and best < 0 and depth > 0:
            is_dead = lambda pos: any(pos.value(m) >= MATE_LOWER for m in pos.gen_moves())
            if all(is_dead(pos.move(m)) for m in pos.gen_moves()):
                in_check = is_dead(pos.nullmove())
                best = -MATE_UPPER if in_check else 0

        # Table part 2
        if best >= gamma:
            self.tp_score[(pos, depth, root)] = Entry(best, entry.upper)
        if best < gamma:
            self.tp_score[(pos, depth, root)] = Entry(entry.lower, best)

        return best

    # secs over maxn is a breaking change. Can we do this?
    # I guess I could send a pull request to deep pink
    # Why include secs at all?
    def _search(self, pos):
        """ Iterative deepening MTD-bi search """
        self.nodes = 0

        # In finished games, we could potentially go far enough to cause a recursion
        # limit exception. Hence we bound the ply.
        for depth in range(1, 1000):
            self.depth = depth
            # The inner loop is a binary search on the score of the position.
            # Inv: lower <= score <= upper
            # 'while lower != upper' would work, but play tests show a margin of 20 plays better.
            lower, upper = -MATE_UPPER, MATE_UPPER
            while lower < upper - EVAL_ROUGHNESS:
                gamma = (lower+upper+1)//2
                score = self.bound(pos, gamma, depth)
                if score >= gamma:
                    lower = score
                if score < gamma:
                    upper = score
            # We want to make sure the move to play hasn't been kicked out of the table,
            # So we make another call that must always fail high and thus produce a move.
            score = self.bound(pos, lower, depth)

            # Yield so the user may inspect the search
            yield

    def search(self, pos, secs):
        start = time.time()
        for _ in self._search(pos):
            if time.time() - start > secs:
                break
        # If the game hasn't finished we can retrieve our move from the
        # transposition table.
        return self.tp_move.get(pos), self.tp_score.get((pos, self.depth, True)).lower


###############################################################################
# User interface
###############################################################################

# Python 2 compatability
if sys.version_info[0] == 2:
    input = raw_input
    class NewOrderedDict(OrderedDict):
        def move_to_end(self, key):
            value = self.pop(key)
            self[key] = value
    OrderedDict = NewOrderedDict


def parse(c):
    fil, rank = ord(c[0]) - ord('a'), int(c[1]) - 1
    return A1 + fil - 10*rank


def render(i):
    rank, fil = divmod(i - A1, 10)
    return chr(fil + ord('a')) + str(-rank + 1)


def print_pos(pos):
    print()
    uni_pieces = {'R':'♜', 'N':'♞', 'B':'♝', 'Q':'♛', 'K':'♚', 'P':'♟',
                  'r':'♖', 'n':'♘', 'b':'♗', 'q':'♕', 'k':'♔', 'p':'♙', '.':'·'}
    for i, row in enumerate(pos.board.split()):
        print(' ', 8-i, ' '.join(uni_pieces.get(p, p) for p in row))
    print('    a b c d e f g h \n\n')

def four_point_transform(image, pts):
        # obtain a consistent order of the points and unpack them
        # individually
        rect = order_points(pts)
        (tl, tr, br, bl) = rect

        maxWidth = w
        maxHeight = h

        dst = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]], dtype = "float32")

        # compute the perspective transform matrix and then apply it
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

        # return the warped image
        return warped
#------------------------------------------------------------------------------------resize_and_threshold_warped
def resize_and_threshold_warped(image):
        #Resize the corrected image to proper size & convert it to grayscale
        #warped_new =  cv2.resize(image,(w/2, h/2))
        warped_new_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        #Smoothing Out Image
        blur = cv2.GaussianBlur(warped_new_gray,(5,5),0)

        #Calculate the maximum pixel and minimum pixel value & compute threshold
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(blur)
        threshold = (min_val + max_val)/2

        #Threshold the image
        ret, warped_processed = cv2.threshold(warped_new_gray, threshold, 255, cv2.THRESH_BINARY)

        #return the thresholded image
        return warped_processed
#---------------------------------------------------------------------------------------------------order_points
def order_points(pts):
        # initialzie a list of coordinates that will be ordered
        # such that the first entry in the list is the top-left,
        # the second entry is the top-right, the third is the
        # bottom-right, and the fourth is the bottom-left
        rect = np.zeros((4, 2), dtype = "float32")

        # the top-left point will have the smallest sum, whereas
        # the bottom-right point will have the largest sum
        s = pts.sum(axis = 1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        # now, compute the difference between the points, the
        # top-right point will have the smallest difference,
        # whereas the bottom-left will have the largest difference
        diff = np.diff(pts, axis = 1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        # return the ordered coordinates
        return rect
#---------------------------------------------------------------------------------------------------duzlestir
#def duzlestir(img):
#    while(True):
#        im2, contours, hierarchy = cv2.findContours(img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
#
#        biggest = None
#        max_area = 0
#        for i in contours:
#                area = cv2.contourArea(i)
#                peri = cv2.arcLength(i,True)
#                approx = cv2.approxPolyDP(i,0.02*peri,True)
#                if area > max_area and len(approx)==4:
#                        biggest = approx
#                        max_area = area
#                        #print max_area
#                        #if max_area>5000:
#                                #cv2.drawContours(img,[approx],0,(0,0,255),2)
#                        warped = four_point_transform(img, approx.reshape(4, 2))
#                        warped_eq = resize_and_threshold_warped(warped)
#        if max_area>100000:
#        	cv2.imwrite('square.jpg', img)
#            cv2.imwrite("Corrected.jpg", warped)
	#	    break;
    #    img = take_image()
    #return warped
#---------------------------------------------------------------------------------------------------takeimage
def take_image():
        cap = cv2.VideoCapture(1)
        while(cap.isOpened()):
            ret,img = cap.read()
            gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
            #gray = cv2.GaussianBlur(gray,(5,5),0)
    	    thresh = cv2.adaptiveThreshold(gray,255,1,1,11,2)
            gray = cv2.bilateralFilter(gray, 11, 17, 17)
            #thresh = cv2.Canny(gray, 30, 200)
            im2, contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            biggest = None
            max_area = 0
            for i in contours:
               area = cv2.contourArea(i)
               peri = cv2.arcLength(i,True)
               approx = cv2.approxPolyDP(i,0.02*peri,True)
               if area > max_area and len(approx)==4:
                   biggest = approx
                   max_area = area
                   warped = four_point_transform(img, approx.reshape(4, 2))
                   warped_eq = resize_and_threshold_warped(warped)
                   cv2.imshow("Corrected Perspective", warped)
            if max_area>100000:
                print ("ok")
                break
        #img = cv2.imread('/home/niyazi/Desktop/takedeneme.jpeg',1)
        return warped
#---------------------------------------------------------------------------------------------------arrayecevir
def arrayecevir(img,harfler):
    durumArray = np.zeros(64).reshape(8,8) #row,column
    genVer = np.hsplit(img, 8)
    #horizontal olarak bolunen arrayi atama yapildi
    for i in range(0,8):
        vars()[harfler[i]] = genVer[i]
    #vertical olarak bolme
    for i in range(0,8):
        dummy = str(harfler[i] + 'Ver')
        vars()[dummy] =np.vsplit(vars()[harfler[i]],8)

    #vertical olarak bolunen arrayi horizontal bolme
    for j in range(0,8):
        for i in range(0,8):
            dummy1 = str(harfler[j]+ str(8-i) )
            dummy2 = str(harfler[j]+ 'Ver')
            vars()[dummy1] = vars()[dummy2][i]
    #bolunmus arraylerin average alma
    for j in range(0,8):
        for i in range(0,8):
            dummy = str(harfler[j]+ str(8-i))
            durumArray[i,j] = np.average(vars()[dummy])/255
    #durumArrayAverage = np.average(durumArray)
    for j in range(0,8):
        for i in range(0,8):

            if(durumArray[i,j]>0.1): #0.28
                durumArray[i,j] = 1
            else:
                durumArray[i,j] = 0

    return durumArray
#---------------------------------------------------------------------------------------------------detect_movement2li
def detect_movement(a,b,harfler,numaralar):

    for i in range(8):
        for j in range(8):
            if(a[i,j]!=b[i,j]):
                if(a[i,j] == 1 and b[i,j] == 0): #ilk durum 1 ken son durum 0 ise o noktadan ayrilmistir
                    #print i,j
                    #print "buradan ayrildi " + harf[j], str(numara[i])
                    buradan = harfler[j] + str(numaralar[i])
                if(a[i,j] == 0 and b[i,j] == 1): # ilk durumda tas yokken o noktaya geldiyse oraya gelmistir
                    #print i,j
                    #print "buraya geldi " + harf[j], str(numara[i])
                    buraya = harfler[j] + str(numaralar[i])
    return buradan+buraya
    #return "e2e4"
#---------------------------------------------------------------------------------------------------detect_movement3lu
def detect_movement2(a,b,c,harfler,numaralar):
    #buradan2 = None ; buraya2 = None
    for i in range(8):
        for j in range(8):
            if(b[i,j]!=c[i,j]):
                if(a[i,j] == 1 and b[i,j] == 1 and c[i,j] == 0): #ilk durum 1 ken son durum 0 ise o noktadan ayrilmistir
                    buradan2 = harfler[jh] + str(numaralar[i])
                        #print i,j
                        #print "buradan ayrildi " + harf[j], str(numara[i])

                        #print buradan
                if(a[i,j] == 1 and b[i,j] == 0 and c[i,j] == 1): # ilk durumda tas yokken o noktaya geldiyse oraya gelmistir
                    buraya2 =  harfler[j] + str(numaralar[i])
                        #print i,j
                        #print "buraya geldi " + harf[j], str(numara[i])
                        #print buraya
    #buraya2 = "niyazi"; buradan2 = "utku"
    return buradan2+buraya2
    #return "e4d5"
#--------------------------------------------------------------------------------------------------button info
def buttonInfo():
    ser.write('isPressed')
    arduinoData = ser.readline()
    if(arduinoData.rstrip('\r\n') == "get"):
	data = "get";
    if(arduinoData.rstrip('\r\n') == "finish"):
	data = "finish";
    if(arduinoData.rstrip('\r\n') == "no"):
	data = "no";
    return data
#-------------------------------------------------------------------------------------------------hamle yap
def hamle_yap():
    print("basladi")
    thresh = take_image()
    edged = cv2.Canny(thresh,5,200)
    cv2.imwrite("corrr2.jpg",edged)
    drmArray = arrayecevir(edged,harf)#duzlestirme islemi yapmayi unutma
    print(drmArray)
    while True:
        info = buttonInfo()
        if(info == "get"):
            break
        if(info == "finish"):
            break
    print(info)
    if(info == "finish"):     # burdan sonra iki defa foto çekiyor onu hallet
        thresh2 = take_image()
        edged2 = cv2.Canny(thresh2,5,200)
        drmArray2 = arrayecevir(edged2,harf)
        print(drmArray2)
        hamle = detect_movement(drmArray,drmArray2,harf,numara)
    elif(info == "get"):
        thresh3 = take_image()
        edged3 = cv2.Canny(thresh3,5,200)
        drmArray3 = arrayecevir(edged3,harf)
        while True:
            info2 = buttonInfo()
            if(info2== "finish"):
                break
        if(info2 == "finish"):
            thresh4 = take_image()
            edged4 = cv2.Canny(thresh4,5,200)
            drmArray4 = arrayecevir(edged4,harf)
            hamle = detect_movement2(drmArray,drmArray3,drmArray4,harf,numara)
    else:
        print("error")
    print (hamle)
    return hamle
def main():
    pos = Position(initial, 0, (True,True), (True,True), 0, 0)
    searcher = Searcher()
    while True:
        print_pos(pos)

        if pos.score <= -MATE_LOWER:
            print("You lost")
            break

        # We query the user until she enters a (pseudo) legal move.
        move = None
        while move not in pos.gen_moves():

            match = re.match('([a-h][1-8])'*2, hamle_yap())
            if match:
                move = parse(match.group(1)), parse(match.group(2))
            else:
                # Inform the user when invalid input (e.g. "help") is entered
                print("Please enter a move like g8f6")
        pos = pos.move(move)

        # After our move we rotate the board and print it again.
        # This allows us to see the effect of our move.
        print_pos(pos.rotate())

        if pos.score <= -MATE_LOWER:
            print("You won")
            break

        # Fire up the engine to look for a move.
        move, score = searcher.search(pos, secs=2)

        if score == MATE_UPPER:
            print("Checkmate!")

        # The black player moves from a rotated position, so we have to
        # 'back rotate' the move before printing it.
        # print("My move:", render(119-move[0]) + render(119-move[1]))
	print(render(119-move[0])) #from
	print(render(119-move[1])) #to
        pos = pos.move(move)



main()
