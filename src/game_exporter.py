"""game_exporter.py

Exports a Lichess game in a human-readable format to stdout.
"""

import json
import sys

from typing import Dict

import lichess.api
import requests.exceptions

from data_models import (Clock, Color, Division, Game, Judgment, Move,
                         MoveAnalysis, Opening, Player, PlayerGameAnalysis,
                         User)


def get_game_object_from_lichess(game_id: str) -> Dict | None:
    try:
        result = lichess.api.game(game_id)
    except requests.exceptions.ConnectionError:
        return None
    return result


def create_game_from_json(json_game) -> Game:
    game = Game()
    if "analysis" in json.dumps(json_game):
        game.has_analysis = True

    ###########
    # PLAYERS
    #
    json_player = json_game["players"]["white"]
    player_game_analysis = PlayerGameAnalysis()
    if game.has_analysis:
        player_game_analysis = PlayerGameAnalysis(
            json_player.get("analysis", {}).get("inaccuracy", -1),
            json_player.get("analysis", {}).get("mistake", -1),
            json_player.get("analysis", {}).get("blunder", -1),
            json_player.get("analysis", {}).get("acpl", -1),
        )
    player_white = Player(
        Color.WHITE,
        User(
            json_player["user"]["name"],
            json_player["user"]["id"]
        ),
        json_player["rating"],
        json_player["ratingDiff"],
        player_game_analysis
    )

    json_player = json_game["players"]["black"]
    player_game_analysis = PlayerGameAnalysis()
    if game.has_analysis:
        player_game_analysis = PlayerGameAnalysis(
            json_player.get("analysis", {}).get("inaccuracy", -1),
            json_player.get("analysis", {}).get("mistake", -1),
            json_player.get("analysis", {}).get("blunder", -1),
            json_player.get("analysis", {}).get("acpl", -1),
        )
    player_black = Player(
        Color.BLACK,
        User(
            json_player["user"]["name"],
            json_player["user"]["id"]
        ),
        json_player["rating"],
        json_player["ratingDiff"],
        player_game_analysis
    )

    #########
    # MOVES
    #
    moves_sans = json_game["moves"].split(" ")
    moves_clocks = json_game["clocks"]
    moves_analyses = json_game.get("analysis")

    moves = []
    move_white = None
    color = Color.WHITE
    for idx, move_san in enumerate(moves_sans):
        thinking_time_cs = moves_clocks[idx] - moves_clocks[idx - 2] if idx >= 2 else 0  # noqa
        move_analysis = MoveAnalysis()
        if game.has_analysis and idx < len(moves_analyses):
            move_analysis = MoveAnalysis(
                moves_analyses[idx].get("eval"),
                moves_analyses[idx].get("mate"),
                moves_analyses[idx].get("best"),
                moves_analyses[idx].get("variation"),
                Judgment(
                    moves_analyses[idx]["judgment"]["name"],
                    moves_analyses[idx]["judgment"]["comment"],
                ) if moves_analyses[idx].get("judgment") else None
            )

        move = Move(
            move_san,
            moves_clocks[idx],
            thinking_time_cs,
            move_analysis
        )

        if color == Color.WHITE:
            color = Color.BLACK
            move_white = move
        else:
            color = Color.WHITE
            moves.append((move_white, move))
            move_white = None
    if move_white:  # No last black move
        moves.append((move_white, None))

    ################
    # GAME DETAILS
    #
    opening = Opening(
        eco=json_game["opening"].get("eco", ""),
        name=json_game["opening"].get("name", ""),
        ply=json_game["opening"].get("ply", 0)
    )

    clock = Clock(
        initial=json_game["clock"].get("initial", -1),
        increment=json_game["clock"].get("increment", -1),
        total_time=json_game["clock"].get("totalTime", -1)
    )

    division = Division(
        middle=json_game["division"].get("middle"),
        end=json_game["division"].get("end")
    )

    game.id = json_game.get("id", "N/A")
    game.clock = clock
    game.moves = moves
    game.rated = json_game.get("rated", True)
    game.variant = json_game.get("variant", "N/A")
    game.speed = json_game.get("speed", "N/A")
    game.status = json_game.get("status", "N/A")
    game.players = (player_white, player_black)
    game.winner = None
    game.opening = opening
    game.division = division

    winner_str = json_game.get("winner", "")
    if winner_str == "white":
        game.winner = Color.WHITE
    if winner_str == "black":
        game.winner = Color.BLACK

    return game


if __name__ == "__main__":
    if len(sys.argv) > 1:
        GAME_ID = sys.argv[1]
    else:
        print("Please supply the Lichess game ID as argument.")
        sys.exit(0)

    json_game = get_game_object_from_lichess(GAME_ID)
    if not json_game:
        print("ERROR: Could not contact Lichess! Stopping...")
        sys.exit(-1)
    # print(json.dumps(json_game, indent=2))
    game = create_game_from_json(json_game)
    print()
    print(game.to_console())
