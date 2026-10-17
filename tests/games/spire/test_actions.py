from raven.games.spire.actions import is_legal, legal_commands, live_monster_indexes


def test_combat_commands(state):
    assert sorted(legal_commands(state("combat"))) == sorted([
        "PLAY 1 0",  # Strike at the Jaw Worm
        "PLAY 1 2",  # Strike at the live Cultist
        "PLAY 2",  # Defend needs no target
        "POTION Use 0 0",
        "POTION Use 0 2",
        "POTION Use 1",
        "END",
    ])


def test_card_indexes_are_one_based_and_targets_zero_based(state):
    commands = legal_commands(state("combat"))
    assert "PLAY 0" not in commands
    assert not any(c.startswith("PLAY 3") for c in commands)  # Bash isn't playable


def test_dead_gone_and_half_dead_monsters_are_not_targets(state):
    message = state("combat")
    assert live_monster_indexes(message["game_state"]) == [0, 2]
    message["game_state"]["combat_state"]["monsters"][2]["half_dead"] = True
    assert live_monster_indexes(message["game_state"]) == [0]
    assert "PLAY 1 2" not in legal_commands(message)


def test_no_targets_left_means_no_targeted_plays(state):
    message = state("combat")
    for monster in message["game_state"]["combat_state"]["monsters"]:
        monster["is_gone"] = True
    commands = legal_commands(message)
    assert not any(c.startswith("PLAY 1") for c in commands)
    assert "PLAY 2" in commands


def test_play_needs_play_available(state):
    message = state("combat")
    message["available_commands"] = ["end", "state"]
    assert legal_commands(message) == ["END"]


def test_card_reward_choices_and_skip(state):
    assert legal_commands(state("card_reward")) == [
        "CHOOSE 0", "CHOOSE 1", "CHOOSE 2", "RETURN",
    ]


def test_potion_reward_skipped_when_slots_are_full(state):
    commands = legal_commands(state("combat_reward_full_potions"))
    assert commands == ["CHOOSE 0", "CHOOSE 2", "PROCEED"]


def test_potion_reward_offered_with_an_empty_slot(state):
    message = state("combat_reward_full_potions")
    message["game_state"]["potions"][2] = {"id": "Potion Slot", "can_use": False}
    assert "CHOOSE 1" in legal_commands(message)


def test_command_aliases_count_as_available(state):
    message = state("card_reward")
    message["available_commands"] = ["choose", "skip", "confirm"]
    commands = legal_commands(message)
    assert "RETURN" in commands and "PROCEED" in commands


def test_nothing_legal_out_of_game_or_when_not_ready(state):
    assert legal_commands(state("main_menu")) == []
    message = state("combat")
    message["ready_for_command"] = False
    assert legal_commands(message) == []


def test_game_over_only_proceeds(state):
    assert legal_commands(state("game_over")) == ["PROCEED"]


def test_is_legal_ignores_case_and_spacing(state):
    message = state("combat")
    assert is_legal(message, "play  1 0")
    assert is_legal(message, "end")
    assert not is_legal(message, "PLAY 3 0")
    assert not is_legal(message, "PLAY 1 1")  # that Cultist is gone
