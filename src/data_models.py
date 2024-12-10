import urllib.parse

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple

import chess

WHITE_KING, WHITE_QUEEN, WHITE_ROOK, WHITE_BISHOP, WHITE_KNIGHT, WHITE_PAWN = "♔♕♖♗♘♙"  # noqa
BLACK_KING, BLACK_QUEEN, BLACK_ROOK, BLACK_BISHOP, BLACK_KNIGHT, BLACK_PAWN = "♚♛♜♝♞♟"  # noqa


class Color(Enum):
    WHITE = "white"
    BLACK = "black"


@dataclass
class Clock:
    initial: int = -1
    increment: int = -1
    total_time: int = -1


@dataclass
class Division:
    middle: int = -1
    end: int = -1


@dataclass
class Opening:
    eco: str = ""
    name: str = ""
    ply: int = ""


@dataclass
class PlayerGameAnalysis:
    inaccuracy: int = -1
    mistake: int = -1
    blunder: int = -1
    acpl: int = -1


@dataclass
class User:
    name: str = ""
    id: str = ""


@dataclass
class Player:
    color: Color = Color.WHITE
    user: User = field(default_factory=User)
    rating: int = -1
    rating_diff: int = 0
    analysis: PlayerGameAnalysis = field(default_factory=PlayerGameAnalysis)


@dataclass
class Judgment:
    name: str | None = None
    comment: str | None = None


@dataclass
class MoveAnalysis:
    eval: int | None = None
    mate: int | None = None
    best: str | None = None
    variation: str | None = None
    judgement: Judgment | None = None

    def __bool__(self) -> bool:
        return any(
            (
                self.eval is not None,
                self.mate is not None,
                self.best is not None,
                self.variation is not None,
                self.judgement is not None
            )
        )


@dataclass
class Move:
    san: str = ""
    clock_centosec: int = 0
    thinking_time_centoseconds: int = 0
    analysis: MoveAnalysis = field(default_factory=MoveAnalysis)

    def _centoseconds_to_timestr(self, value: int) -> str:
        total_seconds = value / 100
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds - 3600 * hours) // 60)
        seconds = total_seconds - 3600 * hours - 60 * minutes
        return (
            f"""{str(hours) + ":" if hours > 0 else ""}"""
            f"{minutes:02d}:{seconds:04.1f}"
        )

    def format_evaluation(self) -> str:
        out = ""
        if self.analysis:
            if self.analysis.mate is not None:
                out = f" #{self.analysis.mate}"
            elif self.analysis.eval is not None:
                out = str(self.analysis.eval / 100)
                if not out.startswith("-"):
                    return " " + out
        return out

    def get_decorated_move(self):
        out = self.san
        if self.analysis.judgement:
            if self.analysis.judgement.name == "Inaccuracy":
                out += "?!"
            if self.analysis.judgement.name == "Mistake":
                out += "?"
            if self.analysis.judgement.name == "Blunder":
                out += "??"
        return out

    @property
    def clock(self) -> str:
        return self._centoseconds_to_timestr(self.clock_centosec)

    @property
    def thinking_time(self) -> str:
        return self._centoseconds_to_timestr(self.thinking_time_centoseconds)


@dataclass
class Game:
    id: str = ""
    rated: bool = True
    variant: str = ""
    speed: str = ""
    perf: str = ""
    created_at: int = -1
    last_move_at: int = -1
    status: str = ""
    source: str = ""
    players: Tuple[Player] = field(default_factory=tuple)
    winner: Color | None = None
    moves: List[Tuple[Move, Move | None]] = field(default_factory=list)
    clock: Clock = field(default_factory=Clock)
    division: Division = field(default_factory=Division)
    opening: Opening = field(default_factory=Opening)
    has_analysis: bool = False

    def board_at_end(self) -> Tuple[chess.Board, str]:
        start_positions = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"  # noqa
        board = chess.Board(start_positions)
        for move_white, move_black in self.moves:
            board.push_san(move_white.san)
            if move_black:
                board.push_san(move_black.san)

        # Create board, replace letters with Unicode symbols:
        board_str = str(board)
        board_str = board_str.replace("k", BLACK_KING)
        board_str = board_str.replace("q", BLACK_QUEEN)
        board_str = board_str.replace("r", BLACK_ROOK)
        board_str = board_str.replace("b", BLACK_BISHOP)
        board_str = board_str.replace("n", BLACK_KNIGHT)
        board_str = board_str.replace("p", BLACK_PAWN)
        board_str = board_str.replace("K", WHITE_KING)
        board_str = board_str.replace("Q", WHITE_QUEEN)
        board_str = board_str.replace("R", WHITE_ROOK)
        board_str = board_str.replace("B", WHITE_BISHOP)
        board_str = board_str.replace("N", WHITE_KNIGHT)
        board_str = board_str.replace("P", WHITE_PAWN)
        # Add color legend:
        board_lines = board_str.split("\n")
        board_lines[3] += "   " + WHITE_PAWN + ": white"
        board_lines[4] += "   " + BLACK_PAWN + ": black"

        return (board, "\n".join(board_lines))

    def to_console(self):
        player_white, player_black = self.players

        # Moves info:
        moves_txt = ""
        move_counter = 1
        for move_white, move_black in self.moves:
            if not move_black:
                move_black = Move()
            # Counter + san:
            san_deco_white = move_white.get_decorated_move()
            san_deco_black = move_black.get_decorated_move()
            moves_txt += f"{move_counter:>3}. {san_deco_white:<8} {san_deco_black:<8}"
            # Clock:
            clock_white = move_white.clock
            clock_black = move_black.clock if move_black.san else ' ' * len(move_white.clock)
            moves_txt += f"   {clock_white}   {clock_black}"
            # Evaluation + comments:
            if self.has_analysis:
                eval_white = move_white.format_evaluation()
                eval_black = move_black.format_evaluation()
                moves_txt += f"   {eval_white:<6}  {eval_black:<6}"
                if move_white.analysis.judgement:
                    moves_txt += f"   White: {move_white.analysis.judgement.comment}"
                if move_black.analysis.judgement:
                    moves_txt += f"   Black: {move_black.analysis.judgement.comment}"
            moves_txt += "\n"
            move_counter += 1

        # Game ending info:
        score_white = "½"
        score_black = "½"
        pretty_endings = {
            "draw": "draw",
            "stalemate": "stalemate",
            "mate": "was checkmated",
            "resign": "resigned",
            "outoftime": "ran out of time"
        }

        if self.winner:
            winner_str = self.winner.value
            if self.winner == Color.WHITE:
                score_white = "1"
                score_black = "0"
                loser_str = Color.BLACK.value
            else:
                score_white = "0"
                score_black = "1"
                loser_str = Color.WHITE.value
            game_ending = f"{winner_str.capitalize()} wins: {loser_str} {pretty_endings[self.status]}"
        else:
            game_ending = f"The game ended with a {self.status.capitalize()}"

        # Render:
        white_player_and_rating = f"{player_white.user.name[:25]} ({player_white.rating})"
        black_player_and_rating = f"{player_black.user.name[:25]} ({player_black.rating})"
        time_control = f"{self.clock.initial // 60}+{self.clock.increment}"
        rated = "RATED" if self.rated else "NOT RATED"
        out = ""
        out += f"LICHESS.ORG · {time_control} · {self.speed.upper()} · {rated}\n"
        out += "\n"
        # Players summary:
        out += f"WHITE: {white_player_and_rating:<32} BLACK: {black_player_and_rating}\n"
        out += (f"  Score..............: {score_white}"
                f"                  Score..............: {score_black}\n")
        out += (f"  Rating change......: {player_white.rating_diff:<3}"
                f"                Rating change......: {player_black.rating_diff}\n")
        if self.has_analysis:
            out += (f"  Inaccuracies.......: {player_white.analysis.inaccuracy:<3}"
                    f"                Inaccuracies.......: {player_black.analysis.inaccuracy}\n")
            out += (f"  Mistakes...........: {player_white.analysis.mistake:<3}"
                    f"                Mistakes...........: {player_black.analysis.mistake}\n")
            out += (f"  Blunders...........: {player_white.analysis.blunder:<3}"
                    f"                Blunders...........: {player_black.analysis.blunder}\n")
            out += (f"  AvgLostCentiPawns..: {player_white.analysis.acpl:<3}"
                    f"                AvgLostCentiPawns..: {player_black.analysis.acpl}\n")
        else:
            out += "\nThis game has not been analyzed, so analysis data is unavailable.\n"
        out += "\n"
        out += f"Opening: [{self.opening.eco}] {self.opening.name}\n\n"

        # Add moves:
        out += moves_txt + "\n"

        # Add game ending:
        out += f"*** {game_ending} ***" + "\n"

        # Add middlegame and endgame info:
        out += "\n"
        if self.division.middle:
            move_no = self.division.middle // 2 + 1
            white_or_black = "black" if self.division.middle % 2 == 0 else "white"
            out += f"Middlegame started at move {move_no} ({white_or_black})\n"
        if self.division.end:
            move_no = self.division.end // 2 + 1
            white_or_black = "black" if self.division.end % 2 == 0 else "white"
            out += f"Endgame started at move {move_no} ({white_or_black})\n"

        # Add board:
        board, board_unicode = self.board_at_end()
        last_move_uci = board.move_stack[-1].uci()
        board_fen = board.board_fen()
        board_gif_url = f"GIF: https://lichess.org/export/fen.gif?fen={urllib.parse.quote_plus(board_fen)}&lastMove={last_move_uci}"  # noqa
        out += "\nFinal position:\n"
        out += board_unicode + "   " + board_gif_url + "\n"
        out += "\n"

        # Add game source URL:
        out += f"Game URL: https://lichess.org/{self.id}\n"
        out += "\n"

        return out
