"""Legal-action tests on real states recorded from a game run (fixtures/real/)."""

import random

import pytest

from raven.games.spire.actions import legal_commands
from raven.games.spire.random_player import RandomPlayer

EXPECTED = {
    "neow_event": ["CHOOSE 0", "CHOOSE 1"],
    "map_start": ["CHOOSE 0", "CHOOSE 1", "CHOOSE 2", "RETURN"],
    "chest": ["CHOOSE 0", "PROCEED"],
    "shop_room": ["CHOOSE 0", "PROCEED"],
    "event_choices": ["CHOOSE 0", "CHOOSE 1", "CHOOSE 2"],
    # Empty potion slots, so the potion reward can be taken.
    "combat_reward_elite": ["CHOOSE 0", "CHOOSE 1", "CHOOSE 2", "CHOOSE 3", "PROCEED"],
    # "skip" is the game's name for RETURN here. "potion" is available but
    # Liquid Bronze can't be used outside combat.
    "card_reward_holding_potion": ["CHOOSE 0", "CHOOSE 1", "CHOOSE 2", "RETURN"],
    "map_holding_potion": ["CHOOSE 0", "CHOOSE 1", "CHOOSE 2", "RETURN"],
    "combat_with_potion": [
        "PLAY 1 0", "PLAY 2 0", "PLAY 3 0", "PLAY 4 0", "PLAY 5", "POTION Use 0", "END",
    ],
    # Out of energy: no "play" in available_commands.
    "combat_only_end": ["END"],
    # The large slime split: index 1 is gone, so targets are 0 and 2. Bash
    # costs more energy than is left.
    "combat_split_slimes": ["PLAY 2 0", "PLAY 2 2", "PLAY 3", "END"],
    "combat_four_gremlins": [
        "PLAY 1", "PLAY 2",
        "PLAY 3 0", "PLAY 3 1", "PLAY 3 2", "PLAY 3 3",
        "PLAY 4",
        "PLAY 5 0", "PLAY 5 1", "PLAY 5 2", "PLAY 5 3",
        "END",
    ],
    "combat_two_gremlins_gone": ["END"],
    "game_over": ["PROCEED"],
    "grid_upgrade": [f"CHOOSE {i}" for i in range(10)],
    # "confirm" is the game's name for PROCEED here. "cancel" is left out:
    # cancelling this step left the real game stuck.
    "grid_upgrade_confirm": ["PROCEED"],
}


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_legal_commands_on_real_states(state, name):
    assert legal_commands(state(f"real/{name}")) == EXPECTED[name]


def test_gone_monsters_are_never_targeted(state):
    for name in ["combat_split_slimes", "combat_two_gremlins_gone"]:
        message = state(f"real/{name}")
        monsters = message["game_state"]["combat_state"]["monsters"]
        gone = {i for i, m in enumerate(monsters) if m["is_gone"]}
        for command in legal_commands(message):
            parts = command.split()
            if parts[0] == "PLAY" and len(parts) == 3:
                assert int(parts[2]) not in gone


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_random_player_picks_legal_commands_on_real_states(state, name):
    message = state(f"real/{name}")
    player = RandomPlayer(random.Random(name))
    for _ in range(30):
        assert player.choose(message) in EXPECTED[name]


def test_cancel_offered_on_a_grid_before_confirming(state):
    message = state("real/grid_upgrade")
    message["available_commands"].append("cancel")
    assert "RETURN" in legal_commands(message)
