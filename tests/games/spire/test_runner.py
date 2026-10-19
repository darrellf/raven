import random

from raven.games.spire.actions import legal_commands
from raven.games.spire.protocol import GameClosed
from raven.games.spire.random_player import RandomPlayer
from raven.games.spire.runner import play_one_run, start_command

TIMEOUT = object()


class ScriptedConnection:
    """Plays back messages in order. TIMEOUT means no reply in time."""

    def __init__(self, messages):
        self.messages = list(messages)
        self.sent = []
        self.timeouts = []
        self.started = False

    def start(self):
        self.started = True

    def send(self, command):
        self.sent.append(command)

    def receive(self, timeout=None):
        self.timeouts.append(timeout)
        if not self.messages:
            raise GameClosed()
        message = self.messages.pop(0)
        return None if message is TIMEOUT else message


def run(messages, **kwargs):
    conn = ScriptedConnection(messages)
    result = play_one_run(conn, RandomPlayer(random.Random(0)), **kwargs)
    return conn, result


def test_start_command():
    assert start_command("ironclad", 0, None) == "START IRONCLAD 0"
    assert start_command("silent", 5, "ABC123") == "START SILENT 5 ABC123"


def test_full_short_run(state):
    combat = state("combat")
    conn, result = run(
        [state("main_menu"), combat, state("card_reward"), state("game_over")],
        seed="123",
    )
    assert conn.started
    assert conn.sent[0] == "START IRONCLAD 0 123"
    assert conn.sent[1] in legal_commands(combat)
    assert conn.sent[2] in legal_commands(state("card_reward"))
    assert len(conn.sent) == 3  # nothing sent after game over
    assert (result.outcome, result.floor, result.score) == ("death", 7, 123)


def test_victory(state):
    over = state("game_over")
    over["game_state"]["screen_state"]["victory"] = True
    _, result = run([state("main_menu"), over])
    assert result.outcome == "victory"


def test_waits_while_not_ready(state):
    busy = state("combat")
    busy["ready_for_command"] = False
    conn, _ = run([state("main_menu"), busy, busy, state("game_over")])
    assert conn.sent == ["START IRONCLAD 0"]


def test_error_retries_with_a_different_command(state):
    card_reward = state("card_reward")
    error = {"error": "Invalid command", "ready_for_command": True}
    conn, _ = run([state("main_menu"), card_reward, error, error, error, state("game_over")])
    tries = conn.sent[1:]
    assert len(tries) == 4
    assert len(set(tries)) == 4  # each failed command is avoided after that
    assert all(t in legal_commands(card_reward) for t in tries)


def test_command_that_changes_nothing_is_avoided(state):
    card_reward = state("card_reward")
    conn, _ = run(
        [state("main_menu"), card_reward, card_reward, card_reward, state("game_over")]
    )
    tries = conn.sent[1:]
    assert len(set(tries)) == 3


def test_timeout_asks_for_state(state):
    conn, result = run([state("main_menu"), TIMEOUT, state("game_over")])
    assert conn.sent == ["START IRONCLAD 0", "STATE"]
    assert result.outcome == "death"


def test_gives_up_after_repeated_timeouts(state):
    _, result = run([state("main_menu")] + [TIMEOUT] * 10, max_timeouts=3)
    assert result.outcome == "no_response"


def test_back_at_menu_ends_the_run(state):
    _, result = run([state("main_menu"), state("card_reward"), state("main_menu")])
    assert result.outcome == "left_run"


def test_game_closing_ends_the_run(state):
    _, result = run([state("main_menu"), state("combat")])
    assert result.outcome == "game_closed"


def test_step_limit(state):
    messages = [state("main_menu")]
    for turn in range(10):
        message = state("combat")
        message["game_state"]["combat_state"]["turn"] = turn
        messages.append(message)
    _, result = run(messages, max_steps=5)
    assert (result.outcome, result.steps) == ("step_limit", 5)


def test_gives_up_when_the_game_stays_not_ready(state):
    # Replays the real hang: after the Neow upgrade's confirm step, the game
    # answered every STATE with ready_for_command false.
    stuck = state("real/grid_upgrade")
    stuck["ready_for_command"] = False
    messages = [state("main_menu"), state("real/grid_upgrade"), state("real/grid_upgrade_confirm")]
    messages += [TIMEOUT, stuck] * 10
    conn, result = run(messages, max_timeouts=3)
    assert result.outcome == "no_response"
    assert conn.sent[2] == "PROCEED"  # confirm, never cancel
    assert conn.sent[3:] == ["STATE"] * 3


def test_ready_state_resets_the_timeout_count(state):
    card_reward = state("card_reward")
    messages = [state("main_menu")]
    for _ in range(4):
        messages += [TIMEOUT, TIMEOUT, card_reward]
    messages.append(state("game_over"))
    _, result = run(messages, max_timeouts=2)
    assert result.outcome == "death"


def stuck_rest_upgrade(state):
    """The real sequence from a rest site where the game froze at confirm."""
    grid = state("real/grid_rest_upgrade")
    grid["available_commands"].remove("cancel")  # so the player picks a card
    return [
        state("main_menu"),
        state("real/rest_site"),
        grid,
        TIMEOUT,  # the game sends nothing after a card is picked
        state("real/grid_rest_upgrade_stuck"),  # reply to STATE: not ready
    ]


def test_confirms_a_stuck_grid_confirm_step(state):
    messages = stuck_rest_upgrade(state) + [state("real/rest_site_done"), state("game_over")]
    conn, result = run(messages)
    assert conn.sent[2].startswith("CHOOSE")  # picks a card on the grid
    assert conn.sent[3:] == ["STATE", "PROCEED", "PROCEED"]  # nudge, then leave rest site
    assert result.outcome == "death"


def test_short_wait_after_picking_on_a_grid(state):
    messages = stuck_rest_upgrade(state) + [state("real/rest_site_done"), state("game_over")]
    conn, _ = run(messages, response_timeout=30.0, grid_timeout=3.0)
    # receive calls: menu, rest site, grid, (timeout), stuck, rest done, game over
    assert conn.timeouts[3:6] == [3.0, 3.0, 3.0]  # from the grid pick to a ready state
    assert conn.timeouts[2] == 30.0 and conn.timeouts[6] == 30.0


def test_confirm_nudges_are_limited(state):
    stuck = state("real/grid_rest_upgrade_stuck")
    messages = stuck_rest_upgrade(state) + [TIMEOUT, stuck] * 10
    conn, result = run(messages, max_confirm_nudges=2, max_timeouts=4)
    assert conn.sent.count("PROCEED") == 2
    assert result.outcome == "no_response"


def test_refused_confirm_waits_instead_of_acting_on_an_old_state(state):
    error = {"error": "Not ready", "ready_for_command": True}
    messages = stuck_rest_upgrade(state) + [error, state("real/rest_site_done"), state("game_over")]
    conn, result = run(messages)
    # After the refusal nothing is sent until the next ready state.
    assert conn.sent[3:] == ["STATE", "PROCEED", "PROCEED"]
    assert result.outcome == "death"


def test_not_ready_grid_without_confirm_is_not_nudged(state):
    stuck = state("real/grid_upgrade")
    stuck["ready_for_command"] = False
    messages = [state("main_menu"), state("real/grid_upgrade"), TIMEOUT, stuck, TIMEOUT, stuck]
    conn, _ = run(messages, max_timeouts=2)
    assert "PROCEED" not in conn.sent
