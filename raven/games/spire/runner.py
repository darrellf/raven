"""Play one run: start from the main menu, act until game over, then stop."""

import hashlib
import json
import logging
from dataclasses import dataclass

from raven.games.spire.protocol import GameClosed

log = logging.getLogger(__name__)


@dataclass
class RunResult:
    # "victory", "death", "left_run", "game_closed", "no_response",
    # "stuck" or "step_limit"
    outcome: str
    floor: int | None = None
    score: int | None = None
    steps: int = 0


def state_key(message):
    """A fingerprint of a state, used to spot commands that changed nothing."""
    data = {
        "available": message.get("available_commands"),
        "state": message.get("game_state"),
    }
    return hashlib.sha1(json.dumps(data, sort_keys=True).encode()).hexdigest()


def start_command(character, ascension, seed):
    parts = ["START", character.upper(), str(ascension)]
    if seed:
        parts.append(str(seed))
    return " ".join(parts)


def play_one_run(
    conn,
    player,
    character="IRONCLAD",
    ascension=0,
    seed=None,
    max_steps=20000,
    response_timeout=30.0,
    max_timeouts=5,
    max_errors=20,
):
    """Drive one run with `player` and return a RunResult.

    A command that gets an error, or leaves the state exactly as it was, is
    avoided the next time that state comes up.
    """
    conn.start()
    started = False
    steps = 0
    timeouts = 0
    errors = 0
    last_message = None
    last_key = None
    last_command = None
    avoid = {}  # state key -> commands that failed or did nothing there

    def act(message):
        nonlocal last_command, steps
        key = state_key(message)
        command = player.choose(message, avoid=avoid.get(key, set()))
        if command is None:
            return False
        conn.send(command)
        last_command = command
        steps += 1
        return True

    while True:
        if steps >= max_steps:
            log.warning("stopping: step limit %d reached", max_steps)
            return RunResult("step_limit", steps=steps)

        try:
            message = conn.receive(timeout=response_timeout)
        except GameClosed:
            return RunResult("game_closed", steps=steps)

        if message is None:
            timeouts += 1
            if timeouts > max_timeouts:
                log.warning("stopping: no response after %d requests", max_timeouts)
                return RunResult("no_response", steps=steps)
            log.info("no message for %ss, asking for state", response_timeout)
            conn.send("STATE")
            continue
        timeouts = 0

        if "error" in message:
            errors += 1
            if errors > max_errors:
                log.warning("stopping: %d errors in a row", max_errors)
                return RunResult("stuck", steps=steps)
            if last_key and last_command:
                avoid.setdefault(last_key, set()).add(last_command)
            if message.get("ready_for_command") and last_message:
                if not act(last_message):
                    conn.send("STATE")
            continue

        if not message.get("ready_for_command"):
            continue

        key = state_key(message)
        if key == last_key and last_command:
            log.info("%s changed nothing, avoiding it here", last_command)
            avoid.setdefault(key, set()).add(last_command)
        else:
            errors = 0
        last_message = message
        last_key = key

        if not message.get("in_game"):
            if started:
                log.info("back at the main menu, run is over")
                return RunResult("left_run", steps=steps)
            available = {c.lower() for c in message.get("available_commands", [])}
            if "start" in available:
                command = start_command(character, ascension, seed)
                conn.send(command)
                last_command = command
            continue

        started = True
        game_state = message.get("game_state") or {}
        if game_state.get("screen_type") == "GAME_OVER":
            screen = game_state.get("screen_state") or {}
            outcome = "victory" if screen.get("victory") else "death"
            result = RunResult(
                outcome,
                floor=game_state.get("floor"),
                score=screen.get("score"),
                steps=steps,
            )
            log.info("run over: %s", result)
            return result

        if not act(message):
            log.info("no legal command, waiting for the next state")
