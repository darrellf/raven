import random

from raven.games.spire.actions import legal_commands
from raven.games.spire.random_player import RandomPlayer


def test_always_picks_a_legal_command(state):
    player = RandomPlayer(random.Random(1))
    for name in ["combat", "card_reward", "combat_reward_full_potions", "game_over"]:
        message = state(name)
        for _ in range(50):
            assert player.choose(message) in legal_commands(message)


def test_returns_none_when_nothing_is_legal(state):
    assert RandomPlayer().choose(state("main_menu")) is None


def test_avoids_commands_when_it_can(state):
    message = state("card_reward")
    avoid = {"CHOOSE 0", "CHOOSE 1", "CHOOSE 2"}
    player = RandomPlayer(random.Random(2))
    assert all(player.choose(message, avoid=avoid) == "RETURN" for _ in range(20))


def test_falls_back_when_everything_is_avoided(state):
    message = state("game_over")
    assert RandomPlayer().choose(message, avoid={"PROCEED"}) == "PROCEED"


def test_prefers_playing_cards_to_ending_turn(state):
    player = RandomPlayer(random.Random(3), end_turn_chance=0.1)
    picks = [player.choose(state("combat")) for _ in range(500)]
    assert picks.count("END") < 100
    assert any(p.startswith("PLAY") for p in picks)
