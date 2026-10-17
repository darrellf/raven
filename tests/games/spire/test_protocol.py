"""Protocol tests, including a fake game that drives the real launcher process."""

import io
import json
import queue
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from raven.games.spire.actions import legal_commands
from raven.games.spire.protocol import Connection, GameClosed, StateRecorder

REPO = Path(__file__).resolve().parents[3]
LAUNCHER = REPO / "scripts" / "run_random.py"


def test_connection_sends_ready_then_commands():
    out = io.StringIO()
    conn = Connection(io.StringIO(""), out)
    conn.start()
    conn.send("END")
    assert out.getvalue() == "ready\nEND\n"


def test_connection_parses_messages_and_skips_junk(tmp_path):
    lines = '\nnot json\n[1, 2]\n{"in_game": false, "ready_for_command": true}\n'
    recorder = StateRecorder(tmp_path / "states.jsonl")
    conn = Connection(io.StringIO(lines), io.StringIO(), recorder)
    conn.start()
    assert conn.receive(timeout=5) == {"in_game": False, "ready_for_command": True}
    with pytest.raises(GameClosed):
        conn.receive(timeout=5)
    recorder.close()
    recorded = (tmp_path / "states.jsonl").read_text(encoding="utf-8").splitlines()
    assert recorded == ["not json", "[1, 2]", '{"in_game": false, "ready_for_command": true}']


def test_connection_returns_error_messages():
    conn = Connection(io.StringIO('{"error": "bad", "ready_for_command": true}\n'), io.StringIO())
    conn.start()
    assert conn.receive(timeout=5)["error"] == "bad"


class FakeGame:
    """Stands in for Slay the Spire: launches our process and talks to it."""

    def __init__(self, args, cwd):
        self.proc = subprocess.Popen(
            [sys.executable, str(LAUNCHER), *args],
            cwd=cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        self.lines = queue.Queue()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for line in self.proc.stdout:
            self.lines.put(line.rstrip("\r\n"))
        self.lines.put(None)

    def read_command(self, timeout=10):
        return self.lines.get(timeout=timeout)

    def send(self, message):
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def close(self):
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.wait(timeout=10)


@pytest.fixture
def game(tmp_path):
    game_folder = tmp_path / "game"
    game_folder.mkdir()
    log_dir = tmp_path / "logs"
    fake = FakeGame(["--record", "--seed", "123", "--log-dir", str(log_dir)], game_folder)
    fake.log_dir = log_dir
    yield fake
    fake.close()


def test_fake_game_full_run(game, state):
    # Handshake.
    assert game.read_command() == "ready"

    # Main menu: we start a run.
    game.send(state("main_menu"))
    assert game.read_command() == "START IRONCLAD 0 123"

    # A few combat turns.
    combat = state("combat")
    for turn in range(1, 4):
        combat["game_state"]["combat_state"]["turn"] = turn
        game.send(combat)
        assert game.read_command() in legal_commands(combat)

    # The game rejects a command; we try something else that's legal.
    game.send(combat)
    first = game.read_command()
    game.send({"error": "Invalid command", "ready_for_command": True})
    second = game.read_command()
    assert second in legal_commands(combat)
    assert second != first

    # Card reward, then game over.
    game.send(state("card_reward"))
    assert game.read_command() in legal_commands(state("card_reward"))
    game.send(state("game_over"))

    # We stop after one run without sending anything else.
    assert game.read_command() is None
    assert game.proc.wait(timeout=10) == 0

    log_files = list(game.log_dir.glob("spire-random-*.log"))
    assert len(log_files) == 1
    log_text = log_files[0].read_text(encoding="utf-8")
    assert "run over" in log_text and "death" in log_text

    states = next(game.log_dir.glob("states-*.jsonl")).read_text(encoding="utf-8")
    assert len(states.splitlines()) == 8  # every message the game sent


def test_stray_prints_never_reach_the_game(tmp_path):
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]);"
        "from raven.games.spire.protocol import claim_stdio;"
        "i, o = claim_stdio(); print('oops'); o.write('ready\\n'); o.flush()"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(REPO)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.stdout == "ready\n"
    assert "oops" in result.stderr
