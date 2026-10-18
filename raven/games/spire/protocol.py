"""CommunicationMod protocol: one JSON state per line in, one command per line out.

The game reads our stdout as commands, so nothing else may ever be written
there. `claim_stdio` takes the real stdout for the connection and points
`sys.stdout` at stderr, which CommunicationMod captures into its error log.
"""

import json
import logging
import queue
import sys
import threading

log = logging.getLogger(__name__)


class GameClosed(Exception):
    """The game closed our stdin."""


def claim_stdio():
    """Return (in_stream, out_stream) for talking to the game.

    After this, stray print() calls go to stderr instead of the game.
    """
    in_stream = sys.stdin
    out_stream = sys.stdout
    in_stream.reconfigure(encoding="utf-8", errors="replace")
    out_stream.reconfigure(encoding="utf-8", newline="\n", line_buffering=True)
    sys.stdout = sys.stderr
    return in_stream, out_stream


class StateRecorder:
    """Appends every raw line received from the game to a JSONL file."""

    def __init__(self, path):
        self.path = path
        self._file = open(path, "a", encoding="utf-8")

    def record(self, line):
        self._file.write(line.rstrip("\r\n") + "\n")
        self._file.flush()

    def close(self):
        self._file.close()


class Connection:
    """A line-based connection to CommunicationMod."""

    def __init__(self, in_stream, out_stream, recorder=None):
        self._in = in_stream
        self._out = out_stream
        self._recorder = recorder
        self._lines = queue.Queue()
        self._reader = threading.Thread(target=self._read_lines, daemon=True)
        self._closed = False

    def _read_lines(self):
        try:
            for line in self._in:
                self._lines.put(line)
        finally:
            self._lines.put(None)

    def _write(self, text):
        log.info("send: %s", text)
        self._out.write(text + "\n")
        self._out.flush()

    def start(self):
        """Tell the game we're ready and start reading its messages."""
        self._write("ready")
        self._reader.start()

    def send(self, command):
        self._write(command)

    def receive(self, timeout=None):
        """Return the next message as a dict, or None if `timeout` passes first.

        Raises GameClosed once the game closes our stdin.
        """
        while True:
            if self._closed:
                raise GameClosed()
            try:
                line = self._lines.get(timeout=timeout)
            except queue.Empty:
                return None
            if line is None:
                self._closed = True
                log.info("game closed the connection")
                raise GameClosed()
            line = line.strip()
            if not line:
                continue
            log.debug("recv: %s", line)
            if self._recorder:
                self._recorder.record(line)
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                log.warning("ignoring line that isn't JSON: %.200s", line)
                continue
            if not isinstance(message, dict):
                log.warning("ignoring JSON that isn't an object: %.200s", line)
                continue
            if "error" in message:
                log.warning("game reported error: %s", message["error"])
            return message
