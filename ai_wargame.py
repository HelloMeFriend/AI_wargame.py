from __future__ import annotations
import argparse
import copy
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from time import sleep
from typing import Tuple, TypeVar, Type, Iterable, ClassVar
import random
# import requests

# maximum and minimum values for our heuristic scores (usually represents an end of game condition)
MAX_HEURISTIC_SCORE = 2000000000
MIN_HEURISTIC_SCORE = -2000000000


# This defines the objects used for the game

class UnitType(Enum):
    """Every unit type."""
    AI = 0
    Tech = 1
    Virus = 2
    Program = 3
    Firewall = 4

class Player(Enum):
    """The 2 players."""
    Attacker = 0
    Defender = 1

    def next(self) -> Player:
        """The next (other) player."""
        if self is Player.Attacker:
            return Player.Defender
        else:
            return Player.Attacker

class GameType(Enum):
    AttackerVsDefender = 0
    AttackerVsComp = 1
    CompVsDefender = 2
    CompVsComp = 3
        
##############################################################################################################

@dataclass(slots=True)
class Unit:
    player: Player = Player.Attacker
    type: UnitType = UnitType.Program
    health : int = 9
    # class variable: damage table for units (based on the unit type constants in order)
    damage_table : ClassVar[list[list[int]]] = [
        [3,3,3,3,1], # AI
        [1,1,6,1,1], # Tech
        [9,6,1,6,1], # Virus
        [3,3,3,3,1], # Program
        [1,1,1,1,1], # Firewall
    ]
    # class variable: repair table for units (based on the unit type constants in order)
    repair_table : ClassVar[list[list[int]]] = [
        [0,1,1,0,0], # AI
        [3,0,0,3,3], # Tech
        [0,0,0,0,0], # Virus
        [0,0,0,0,0], # Program
        [0,0,0,0,0], # Firewall
    ]

    def is_alive(self) -> bool:
        """Are we alive ? (Checks health is bigger than 0)"""
        return self.health > 0

    def mod_health(self, health_delta : int):
        """Modify this unit's health by delta amount."""
        self.health += health_delta
        if self.health < 0:
            self.health = 0
        elif self.health > 9:
            self.health = 9

    def to_string(self) -> str:
        """Text representation of this unit."""
        p = self.player.name.lower()[0]
        t = self.type.name.upper()[0]
        return f"{p}{t}{self.health}"
    
    def __str__(self) -> str:
        """Text representation of this unit."""
        return self.to_string()
    
    def damage_amount(self, target: Unit) -> int:
        """How much can this unit damage another unit."""
        amount = self.damage_table[self.type.value][target.type.value]
        if target.health - amount < 0:
            return target.health
        return amount

    def repair_amount(self, target: Unit) -> int:
        """How much can this unit repair another unit."""
        amount = self.repair_table[self.type.value][target.type.value]
        if target.health + amount > 9:
            return 9 - target.health
        return amount

##############################################################################################################

@dataclass(slots=True)
class Coord:
    """Representation of a game cell coordinate (row, col)."""
    row : int = 0
    col : int = 0

    def col_string(self) -> str:
        """Text representation of this Coord's column."""
        coord_char = '?'
        if self.col < 16:
                coord_char = "0123456789abcdef"[self.col]
        return str(coord_char)

    def row_string(self) -> str:
        """Text representation of this Coord's row."""
        coord_char = '?'
        if self.row < 26:
                coord_char = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[self.row]
        return str(coord_char)

    def to_string(self) -> str:
        """Text representation of this Coord."""
        return self.row_string()+self.col_string()
    
    def __str__(self) -> str:
        """Text representation of this Coord."""
        return self.to_string()
    
    def clone(self) -> Coord:
        """Clone a Coord."""
        return copy.copy(self)

    def iter_range(self, dist: int) -> Iterable[Coord]:
        """Iterates over Coords inside a rectangle centered on our Coord."""
        for row in range(self.row-dist,self.row+1+dist):
            for col in range(self.col-dist,self.col+1+dist):
                yield Coord(row,col)

    def iter_adjacent(self) -> Iterable[Coord]:
        """Iterates over adjacent Coords."""
        yield Coord(self.row-1,self.col)
        yield Coord(self.row,self.col-1)
        yield Coord(self.row+1,self.col)
        yield Coord(self.row,self.col+1)

    @classmethod
    def from_string(cls, s : str) -> Coord | None:
        """Create a Coord from a string. ex: D2."""
        s = s.strip()
        for sep in " ,.:;-_":
                s = s.replace(sep, "")
        if (len(s) == 2):
            coord = Coord()
            coord.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coord.col = "0123456789abcdef".find(s[1:2].lower())
            return coord
        else:
            return None

##############################################################################################################

@dataclass(slots=True)
class CoordPair:
    """Representation of a game move or a rectangular area via 2 Coords."""
    src : Coord = field(default_factory=Coord)
    dst : Coord = field(default_factory=Coord)

    def to_string(self) -> str:
        """Text representation of a CoordPair."""
        return self.src.to_string()+" "+self.dst.to_string()
    
    def __str__(self) -> str:
        """Text representation of a CoordPair."""
        return self.to_string()

    def clone(self) -> CoordPair:
        """Clones a CoordPair."""
        return copy.copy(self)

    def iter_rectangle(self) -> Iterable[Coord]:
        """Iterates over cells of a rectangular area."""
        for row in range(self.src.row,self.dst.row+1):
            for col in range(self.src.col,self.dst.col+1):
                yield Coord(row,col)

    @classmethod
    def from_quad(cls, row0: int, col0: int, row1: int, col1: int) -> CoordPair:
        """Create a CoordPair from 4 integers."""
        return CoordPair(Coord(row0,col0),Coord(row1,col1))
    
    @classmethod
    def from_dim(cls, dim: int) -> CoordPair:
        """Create a CoordPair based on a dim-sized rectangle."""
        return CoordPair(Coord(0,0),Coord(dim-1,dim-1))
    
    @classmethod
    def from_string(cls, s : str) -> CoordPair | None:
        """Create a CoordPair from a string. ex: A3 B2"""
        s = s.strip()
        for sep in " ,.:;-_":
                s = s.replace(sep, "")
        if (len(s) == 4):
            coords = CoordPair()
            coords.src.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[0:1].upper())
            coords.src.col = "0123456789abcdef".find(s[1:2].lower())
            coords.dst.row = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".find(s[2:3].upper())
            coords.dst.col = "0123456789abcdef".find(s[3:4].lower())
            return coords
        else:
            return None

##############################################################################################################

@dataclass(slots=True)
class Options:
    """Representation of the game options. (I think this is optional not sure)"""
    dim: int = 5
    max_depth : int | None = 4
    min_depth : int | None = 2
    max_time : float | None = 5.0
    game_type : GameType = GameType.AttackerVsDefender
    alpha_beta : bool = True
    max_turns : int | None = 100
    randomize_moves : bool = True
    broker : str | None = None

##############################################################################################################

@dataclass(slots=True)
class Stats:
    """Representation of the global game statistics."""
    evaluations_per_depth : dict[int,int] = field(default_factory=dict)
    total_seconds: float = 0.0
    minimax_entry: int = 0

    def increment_evaluations(self, depth):
        if depth in self.evaluations_per_depth:
            self.evaluations_per_depth[depth] += 1
        else:
            self.evaluations_per_depth[depth] = 1

##############################################################################################################

@dataclass(slots=True)
class Game:
    """Representation of the game state."""
    board: list[list[Unit | None]] = field(default_factory=list)
    next_player: Player = Player.Attacker
    turns_played : int = 0
    options: Options = field(default_factory=Options)
    stats: Stats = field(default_factory=Stats)
    _attacker_has_ai : bool = True
    _defender_has_ai : bool = True
    score_list = []

    def __post_init__(self):
        """Automatically called after class init to set up the default board state."""
        dim = self.options.dim
        self.board = [[None for _ in range(dim)] for _ in range(dim)]
        md = dim-1
        self.set(Coord(0,0),Unit(player=Player.Defender,type=UnitType.AI))
        self.set(Coord(1,0),Unit(player=Player.Defender,type=UnitType.Tech))
        self.set(Coord(0,1),Unit(player=Player.Defender,type=UnitType.Tech))
        self.set(Coord(2,0),Unit(player=Player.Defender,type=UnitType.Firewall))
        self.set(Coord(0,2),Unit(player=Player.Defender,type=UnitType.Firewall))
        self.set(Coord(1,1),Unit(player=Player.Defender,type=UnitType.Program))
        self.set(Coord(md,md),Unit(player=Player.Attacker,type=UnitType.AI))
        self.set(Coord(md-1,md),Unit(player=Player.Attacker,type=UnitType.Virus))
        self.set(Coord(md,md-1),Unit(player=Player.Attacker,type=UnitType.Virus))
        self.set(Coord(md-2,md),Unit(player=Player.Attacker,type=UnitType.Program))
        self.set(Coord(md,md-2),Unit(player=Player.Attacker,type=UnitType.Program))
        self.set(Coord(md-1,md-1),Unit(player=Player.Attacker,type=UnitType.Firewall))

    def clone(self) -> Game:
        """Make a new copy of a game for minimax recursion.

        Shallow copy of everything except the board (options and stats are shared).
        """
        new = copy.copy(self)
        new.board = copy.deepcopy(self.board)
        return new

    def is_empty(self, coord : Coord) -> bool:
        """Check if contents of a board cell of the game at Coord is empty (must be valid coord)."""
        return self.board[coord.row][coord.col] is None

    #own added function
    def in_combat(self, coord : Coord) -> bool:
        """Check if a unit is in combat (must be valid coord)."""
        unitSrc = self.get(coord)
        for adjacent_coord in coord.iter_adjacent():
            unitDst = self.get(adjacent_coord)
            if self.is_valid_coord(adjacent_coord) and not self.is_empty(adjacent_coord) and unitSrc.player != unitDst.player:
                return True
        return False

    def get(self, coord : Coord) -> Unit | None:
        """Get contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            return self.board[coord.row][coord.col]
        else:
            return None

    def set(self, coord : Coord, unit : Unit | None):
        """Set contents of a board cell of the game at Coord."""
        if self.is_valid_coord(coord):
            self.board[coord.row][coord.col] = unit

    def remove_dead(self, coord: Coord):
        """Remove unit at Coord if dead."""
        unit = self.get(coord)
        if unit is not None and not unit.is_alive():
            self.set(coord,None)
            if unit.type == UnitType.AI:
                if unit.player == Player.Attacker:
                    self._attacker_has_ai = False
                else:
                    self._defender_has_ai = False 

    def mod_health(self, coord : Coord, health_delta : int):
        """Modify health of unit at Coord (positive or negative delta)."""
        target = self.get(coord)
        if target is not None:
            target.mod_health(health_delta)
            self.remove_dead(coord)

    #Valid movements implemented
    def is_valid_move(self, coords : CoordPair) -> bool:
        """Validate a move expressed as a CoordPair. TODO """
        if not self.is_valid_coord(coords.src) or not self.is_valid_coord(coords.dst):
            return False
        unitSrc = self.get(coords.src)
        if unitSrc is None or unitSrc.player != self.next_player:
            return False
        # Necessary implementation for explosion
        if coords.dst == coords.src:
            return True
        # Make sure that targets are within an unit distance
        if abs(coords.src.col - coords.dst.col) > 1:
            return False
        # Check for combat or repair, repair move is only valid if target health < 9
        unitDst = self.get(coords.dst)
        if unitDst is not None and unitDst.health < 9 and unitDst.player.name == unitSrc.player.name and unitSrc.repair_amount(unitDst) > 0:
            return True
        elif unitDst is not None and unitDst.player.name != unitSrc.player.name:
            return True
        elif unitDst is not None and unitDst.player.name == unitSrc.player.name and unitDst.health == 9:
            return False
        elif unitDst is not None and unitDst.player.name == unitSrc.player.name and (unitSrc.repair_amount(unitDst) == 0 or unitDst.health < 9):
            return False
            
        # to check that AI, Firewall, and Program can only move up, left | or down, right (defender) 
        if unitSrc.type.name != "Tech" and unitSrc.type.name != "Virus":
            if unitSrc.player.name == "Attacker" and ((coords.dst.col != coords.src.col - 1) and (coords.dst.row != coords.src.row - 1)):
                return False
            elif unitSrc.player.name == "Defender" and ((coords.dst.col != coords.src.col + 1) and (coords.dst.row != coords.src.row + 1)):
                return False
            # Check if AI, Firewall and Program are engaged in combat
            elif self.in_combat(coords.src):
                    return False
        return True

    def perform_move(self, coords : CoordPair) -> Tuple[bool,str]:
        """Validate and perform a move expressed as a CoordPair. TODO: WRITE MISSING CODE!!!"""
        unitSrc = self.get(coords.src)
        unitDst = self.get(coords.dst)
        if self.is_valid_move(coords):
            # Explosion move performance
            if coords.dst == coords.src:
                for adjacent_coord in coords.src.iter_range(1):
                    self.mod_health(adjacent_coord, -2)
                self.mod_health(coords.src, -unitSrc.health)
            # End of explosion code
            # Bi-directional damage time
            elif unitDst is not None and unitSrc.player != unitDst.player:
                dmg = unitSrc.damage_amount(unitDst)
                sdmg = unitDst.damage_amount(unitSrc)
                self.mod_health(coords.dst, -dmg)
                self.mod_health(coords.src, -sdmg)
            # Repair amount, support moment
            elif unitDst is not None and unitSrc.player == unitDst.player:
                rpr = unitSrc.repair_amount(unitDst)
                self.mod_health(coords.dst, rpr)
            # Moving and setting units around
            else:
                self.set(coords.dst,self.get(coords.src))
                self.set(coords.src,None)
            return (True,"Move executed: " + str(coords))
        return (False,"invalid move")

    def next_turn(self):
        """Transitions game to the next turn."""
        self.next_player = self.next_player.next()
        self.turns_played += 1

    def to_string(self) -> str:
        """Pretty text representation of the game."""
        dim = self.options.dim
        output = ""
        output += f"Next player: {self.next_player.name}\n"
        output += f"Turns played: {self.turns_played}\n"
        coord = Coord()
        output += "\n   "
        for col in range(dim):
            coord.col = col
            label = coord.col_string()
            output += f"{label:^3} "
        output += "\n"
        for row in range(dim):
            coord.row = row
            label = coord.row_string()
            output += f"{label}: "
            for col in range(dim):
                coord.col = col
                unit = self.get(coord)
                if unit is None:
                    output += " .  "
                else:
                    output += f"{str(unit):^3} "
            output += "\n"
        return output

    def __str__(self) -> str:
        """Default string representation of a game."""
        return self.to_string()
    
    def is_valid_coord(self, coord: Coord) -> bool:
        """Check if a Coord is valid within out board dimensions."""
        dim = self.options.dim
        if coord.row < 0 or coord.row >= dim or coord.col < 0 or coord.col >= dim:
            return False
        return True

    def read_move(self) -> CoordPair:
        """Read a move from keyboard and return as a CoordPair."""
        while True:
            s = input(F'Player {self.next_player.name}, enter your move: ')
            coords = CoordPair.from_string(s)
            if coords is not None and self.is_valid_coord(coords.src) and self.is_valid_coord(coords.dst):
                return coords
            else:
                print('Invalid coordinates! Try again.')
    
    def human_turn(self, file):
        """Human player plays a move (or get via broker)."""
        if self.options.broker is not None:
            print("Getting next move with auto-retry from game broker...")
            while True:
                mv = self.get_move_from_broker()
                if mv is not None:
                    (success,result) = self.perform_move(mv)
                    print(f"Broker {self.next_player.name}: ",end='')
                    print(result)
                    file.write(result)
                    file.flush()
                    if success:
                        self.next_turn()
                        break
                sleep(0.1)
        else:
            while True:
                mv = self.read_move()
                (success,result) = self.perform_move(mv)
                if success:
                    print(f"Player {self.next_player.name}: ",end='')
                    print(result)
                    file.write(f"Player {self.next_player.name}: ")
                    file.write(result) 
                    file.flush()
                    self.next_turn()
                    break
                else:
                    print("The move is not valid! Try again.")

    def computer_turn(self, file) -> CoordPair | None:
        """Computer plays a move."""
        mv = self.suggest_move(file)
        if mv is not None:
            (success,result) = self.perform_move(mv)
            if success:
                print(f"Computer {self.next_player.name}: ",end='')
                print(result)
                file.write(result)
                file.flush()
                self.next_turn()
        return mv

    def player_units(self, player: Player) -> Iterable[Tuple[Coord,Unit]]:
        """Iterates over all units belonging to a player."""
        for coord in CoordPair.from_dim(self.options.dim).iter_rectangle():
            unit = self.get(coord)
            if unit is not None and unit.player == player:
                yield (coord,unit)

    def is_finished(self) -> bool:
        """Check if the game is over."""
        return self.has_winner() is not None

    def has_winner(self) -> Player | None:
        """Check if the game is over and returns winner"""
        if self.options.max_turns is not None and self.turns_played >= self.options.max_turns:
            return Player.Defender
        if self._attacker_has_ai:
            if self._defender_has_ai:
                return None
            else:
                return Player.Attacker    
        return Player.Defender

    def move_candidates(self) -> Iterable[CoordPair]:
        """Generate valid move candidates for the next player."""
        move = CoordPair()
        for (src,_) in self.player_units(self.next_player):
            move.src = src
            for dst in src.iter_adjacent():
                move.dst = dst
                if self.is_valid_move(move):
                    yield move.clone()
            move.dst = src
            yield move.clone()

    def move_candidates2(self, player: Player) -> Iterable[CoordPair]:
        """Generate valid move candidates for the next player."""
        move = CoordPair()
        for (src,_) in self.player_units(player):
            move.src = src
            for dst in src.iter_adjacent():
                move.dst = dst
                if self.is_valid_move(move):
                    yield move.clone()
            move.dst = src
            yield move.clone()

    def random_move(self) -> Tuple[int, CoordPair | None, float]:
        """Returns a random move."""
        move_candidates = list(self.move_candidates())
        random.shuffle(move_candidates)
        if len(move_candidates) > 0:
            return (0, move_candidates[0], 1)
        else:
            return (0, None, 0)
        
    def minimax(self, depth, alpha, beta, max_player: bool, time, game: Game):
        """"Implementing minimax with alpha beta pruning algorithm"""
        
        #Increment into the stats array for each array depth
        self.stats.increment_evaluations(depth)

        #check for end state, leaf node 
        if self.is_finished() or depth == 0:
            # returns board score, and best move
            return self.heuristic_e2(game), None

        # Incremets turn but not for the first turn
        if self.stats.minimax_entry != 0:
            self.next_turn()
        self.stats.minimax_entry = 1

        if max_player:
            #Start off with -inf for max player
            score = MIN_HEURISTIC_SCORE
            best_move = None
            #Initial copy of the game to return to 
            game2 = self.clone()
            for move in game2.move_candidates():
                #perform move 
                self.perform_move(move)
                #recursive call, creates branches and nodes until leaf nodes and returns
                (current_score, _) = self.minimax(depth - 1, alpha, beta, False, time, game)
                #Revert the game stat back to its origin
                self = game2.clone()
                #Checks for best move (since the move_candidates function orders the moves it will always return  
                # the FIRST best move)
                if current_score > score:
                    score = current_score
                    best_move = move
                #Keep a copy of the game to bring back to the origin within the loop (first call outside of loop)
                game2 = self.clone()
                #Check for time limit not passed
                tot = (datetime.now() - time).total_seconds()
                if (datetime.now() - time).total_seconds() > self.options.max_time:
                    break
                #Alpha beta option, if turned on, checks for if node beta <= alpha then breaks off the loop if so
                # meaning that  it won't check the rest of that nodes children
                if self.options.alpha_beta == True:
                    alpha = max(alpha, current_score)
                    if beta <= alpha:
                        break           
            return score, best_move
        else:
            #next turn incremement
            score = MAX_HEURISTIC_SCORE
            best_move = None
            game2 = self.clone()
            for move in game2.move_candidates():
                self.perform_move(move)
                (current_score, _) = self.minimax(depth - 1, alpha, beta, True, time, game)
                self = game2.clone()
                if current_score < score:
                    score = current_score
                    best_move = move
                game2 = self.clone()
                tot = (datetime.now() - time).total_seconds()
                if (datetime.now() - time).total_seconds() > self.options.max_time:
                    break
                if self.options.alpha_beta == True:
                    beta = min(beta, current_score)
                    if beta <= alpha:
                        break
            return score, best_move

    # First heuristic given for demo evaluation   
    def heuristic_e0(self, game: Game):
        """"Given Heuristic evaluation: e0"""
        if self.options.game_type == GameType.CompVsDefender:
            nplayer = Player.Defender   
            player = Player.Attacker
        elif self.options.game_type.name == "AttackerVsComp":
            nplayer = Player.Attacker   
            player = Player.Defender
        elif self.options.game_type == GameType.CompVsComp and game.next_player.name == "Attacker":
            nplayer = Player.Defender   
            player = Player.Attacker
        elif self.options.game_type == GameType.CompVsComp and game.next_player.name == "Defender":
            nplayer = Player.Attacker   
            player = Player.Defender

        other = ai = nother = nai = 0
        for coord, unit in self.player_units(player):
            if unit.type.name == "AI":
                ai += 1
            elif unit is not None:
                other += 1
        for coord, unit in self.player_units(nplayer):
            if unit.type.name == "AI":
                nai += 1
            elif unit is not None:
                nother += 1

        return (3*other + 9999*ai) - (3*nother + 9999*nai)
    
    #Heuristic (not good) just for futher testing of code functionality, works simply off the units health
    def heuristic_e1(self, game: Game):
        """"Given Heuristic evaluation: e1"""
        if self.options.game_type == GameType.CompVsDefender:
            nplayer = Player.Defender   
            player = Player.Attacker
        elif self.options.game_type.name == "AttackerVsComp":
            nplayer = Player.Attacker   
            player = Player.Defender
        elif self.options.game_type == GameType.CompVsComp and game.next_player.name == "Attacker":
            nplayer = Player.Defender   
            player = Player.Attacker
        elif self.options.game_type == GameType.CompVsComp and game.next_player.name == "Defender":
            nplayer = Player.Attacker   
            player = Player.Defender

        other = ai = nother = nai = 0
        for coord, unit in self.player_units(player):
            if unit.type.name == "AI":
                ai += unit.health
            elif unit is not None:
                other += unit.health
        for coord, unit in self.player_units(nplayer):
            if unit.type.name == "AI":
                nai += unit.health
            elif unit is not None:
                nother += unit.health
        return (9*other + 99*ai) - (9*nother + 99*nai)
    
    def heuristic_e2(self, game: Game):
        """"Given Heuristic evaluation: e2"""

        if self.options.game_type == GameType.CompVsDefender:
            nplayer = Player.Defender   
            player = Player.Attacker
        elif self.options.game_type.name == "AttackerVsComp":
            nplayer = Player.Attacker   
            player = Player.Defender
        elif self.options.game_type == GameType.CompVsComp and game.next_player.name == "Attacker":
            nplayer = Player.Defender   
            player = Player.Attacker
        elif self.options.game_type == GameType.CompVsComp and game.next_player.name == "Defender":
            nplayer = Player.Attacker   
            player = Player.Defender

        # First part of the heuristic is assigning material balance: health check for pieces
        other = nother = ai = nai = v = nv = p = np = 0
        combat = ncombat = 0
        ai_move = nai_move = 0
        closing = nclosing = 0

        for coord, unit in self.player_units(player):
            
            if unit.type.name == "AI":
                for coords in coord.iter_range(1) :
                    unitDst = self.get(coords)
                    if unitDst is not None and unitDst.player != unit.player.name:
                        closing -= 2

                for coords in coord.iter_range(2):
                    unitDst = self.get(coords)
                    if unitDst is not None and unitDst.player.name != unit.player.name:
                        closing -= 1

            if self.in_combat(coord):
                combat += 1

            for coords in coord.iter_range(1):
                unitDst = self.get(coords)
                if unitDst is not None:
                    other += 1

            if unit.type.name == "AI":
                ai = 1000
            elif unit.type.name == "Virus" or unit.type.name == "Tech":
                v += 2 * unit.health
            elif unit is not None:
                other += unit.health

        for coord, unit in self.player_units(nplayer):

            if unit.type.name == "AI":
                for coords in coord.iter_range(1):
                    unitDst = self.get(coords)
                    if unitDst is not None and unitDst.player.name != unit.player.name:
                        closing -= 2

                for coords in coord.iter_range(2):
                    unitDst = self.get(coords)
                    if unitDst is not None and unitDst.player.name != unit.player.name:
                        closing -= 1

            if self.in_combat(coord):
                ncombat += 1

            for coords in coord.iter_range(1):
                unitDst = self.get(coords)
                if unitDst is not None:
                    other += 1

            if unit.type.name == "AI":
                nai = 1000
            elif unit.type.name == "Virus" or unit.type.name == "Tech":
                nv += 2 * unit.health
            elif unit is not None:
                nother += unit.health

        #Second part of the heuristic is evaluating how many open moves you get
        moves = nmoves = 0
        for move in self.move_candidates2(player):
            moves += 1
        for move in self.move_candidates2(nplayer):
            moves += 1

        #Third part allow for the AI to move

        heur = (other + v + p + ai  + moves + ai_move + combat + closing) - (nother + nv + np + nai  + nmoves + nai_move + ncombat + nclosing)
        return heur
                  
    def suggest_move(self, file) -> CoordPair | None:
        """Suggest the next move using minimax alpha beta. TODO: REPLACE RANDOM_MOVE WITH PROPER GAME LOGIC!!!"""
        start_time = datetime.now()
        ngame = self.clone()   
        eval = 0     
        (score, move) = ngame.minimax(self.options.max_depth, MIN_HEURISTIC_SCORE, MAX_HEURISTIC_SCORE, True, start_time, self)
        self.stats.minimax_entry = 0

        elapsed_seconds = (datetime.now() - start_time).total_seconds()
        self.stats.total_seconds += elapsed_seconds
        score_str = f"Heuristic score: {score}\n"
        print(score_str, end='')
        file.write(score_str)

        total_evals = sum(self.stats.evaluations_per_depth.values())
        cumulative_evals_str = f"Cumulative evals: {total_evals}\n"
        print(cumulative_evals_str, end='')
        file.write(cumulative_evals_str)

        evals_per_depth_str = "Evals per depth: "
        for k in sorted(self.stats.evaluations_per_depth.keys()):
            if k == self.options.max_depth:
                break
            evals_per_depth_str += f"{self.options.max_depth - k}:{self.stats.evaluations_per_depth[k]} "
        print(evals_per_depth_str, end='')
        file.write(evals_per_depth_str + '\n')

        cumulative_percentage_str = "Cumulative % evals per depth: "
        for k in sorted(self.stats.evaluations_per_depth.keys()):
            if k == self.options.max_depth:
                break
            percentage = (self.stats.evaluations_per_depth[k] / total_evals) * 100
            cumulative_percentage_str += f"{self.options.max_depth - k}:{percentage:.1f}% "
        print(cumulative_percentage_str, end='')
        file.write(cumulative_percentage_str + '\n')

        branching_factor = self.stats.evaluations_per_depth[0] / self.stats.evaluations_per_depth[1]
        branching_factor_str = f"Branching factor: {branching_factor:.1f}\n"
        print(branching_factor_str)
        file.write(branching_factor_str)

        file.flush()

        if self.stats.total_seconds > 0:
            print(f"Eval perf.: {total_evals/self.stats.total_seconds/1000:0.1f}k/s")
        print(f"Elapsed time: {elapsed_seconds:0.1f}s")
        return move

    def post_move_to_broker(self, move: CoordPair):
        """Send a move to the game broker."""
        if self.options.broker is None:
            return
        data = {
            "from": {"row": move.src.row, "col": move.src.col},
            "to": {"row": move.dst.row, "col": move.dst.col},
            "turn": self.turns_played
        }
        try:
            r = requests.post(self.options.broker, json=data)
            if r.status_code == 200 and r.json()['success'] and r.json()['data'] == data:
                # print(f"Sent move to broker: {move}")
                pass
            else:
                print(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")

    def get_move_from_broker(self) -> CoordPair | None:
        """Get a move from the game broker."""
        if self.options.broker is None:
            return None
        headers = {'Accept': 'application/json'}
        try:
            r = requests.get(self.options.broker, headers=headers)
            if r.status_code == 200 and r.json()['success']:
                data = r.json()['data']
                if data is not None:
                    if data['turn'] == self.turns_played+1:
                        move = CoordPair(
                            Coord(data['from']['row'],data['from']['col']),
                            Coord(data['to']['row'],data['to']['col'])
                        )
                        print(f"Got move from broker: {move}")
                        return move
                    else:
                        # print("Got broker data for wrong turn.")
                        # print(f"Wanted {self.turns_played+1}, got {data['turn']}")
                        pass
                else:
                    # print("Got no data from broker")
                    pass
            else:
                print(f"Broker error: status code: {r.status_code}, response: {r.json()}")
        except Exception as error:
            print(f"Broker error: {error}")
        return None

##############################################################################################################

def main():
    # parse command line arguments
    parser = argparse.ArgumentParser(
        prog='ai_wargame',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--max_depth', type=int, help='maximum search depth')
    parser.add_argument('--max_time', type=float, help='maximum search time')
    parser.add_argument('--game_type', type=str, default="auto", help='game type: auto|attacker|defender|manual')
    parser.add_argument('--broker', type=str, help='play via a game broker')
    args = parser.parse_args()

    # parse the game type
    if args.game_type == "attacker":
        game_type = GameType.AttackerVsComp
    elif args.game_type == "defender":
        game_type = GameType.CompVsDefender
    elif args.game_type == "manual":
        game_type = GameType.AttackerVsDefender
    else:
        game_type = GameType.CompVsComp

    # set up game options
    options = Options(game_type=game_type)

    # override class defaults via command line options
    if args.max_depth is not None:
        options.max_depth = args.max_depth
    if args.max_time is not None:
        options.max_time = args.max_time
    if args.broker is not None:
        options.broker = args.broker

    # create a new game
    game = Game(options=options)
    print(game)

    #opening file

    file = open("gameTrace-(" + str(options.alpha_beta) + ")-(" + str(options.max_time) + ")-(" + str(options.max_turns) + ")"+".txt", "w")
    # + ")("+ game.options.max_time +")("+ game.options.max_turns + ")" + 
    file.write("The game parameters:\n")
    file.write("--Value of timeout in s: " + str(options.max_time) + "\n")
    file.write("--Max number of turns: " + str(options.max_turns)+ "\n")
    file.write("--Is alpha-beta on : " + str(options.alpha_beta)+ "\n")
    file.write("--Play mode: " + str(game.options.game_type.name)+ "\n\n")
    file.flush()
    # the main game loop
    while True:
        winner = game.has_winner()
        if winner is not None:
            print(f"{winner.name} wins!")
            file.write(f"{winner.name} wins!")
            file.flush()
            break
        if game.options.game_type == GameType.AttackerVsDefender:
            game.human_turn(file)
        elif game.options.game_type == GameType.AttackerVsComp and game.next_player == Player.Attacker:
            game.human_turn(file)
        elif game.options.game_type == GameType.CompVsDefender and game.next_player == Player.Defender:
            game.human_turn(file)
        else:
            player = game.next_player
            move = game.computer_turn(file)
            if move is not None:
                game.post_move_to_broker(move)
            else:
                print("Computer doesn't know what to do!!!")
                exit(1)
        print()
        print(game)
        file.write("\n" + str(game) + "\n")
        file.flush()

##############################################################################################################

if __name__ == '__main__':
    main()
