"""Launcher the game runs: a random player plays one run of Slay the Spire.

CommunicationMod starts this from the game's folder, so everything here uses
absolute paths based on this file's location. Never print: stdout is the
game's command channel. Logs go to <repo>/logs/.

Usage (as the game runs it):
    <repo>/.venv/Scripts/python.exe <repo>/scripts/run_random.py [--record]
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from raven.games.spire.protocol import Connection, StateRecorder, claim_stdio  # noqa: E402
from raven.games.spire.random_player import RandomPlayer  # noqa: E402
from raven.games.spire.runner import play_one_run  # noqa: E402


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--character", default="IRONCLAD")
    parser.add_argument("--ascension", type=int, default=0)
    parser.add_argument("--seed", default=None)
    parser.add_argument(
        "--record",
        action="store_true",
        help="save every raw game state to logs/states-<time>.jsonl",
    )
    parser.add_argument("--log-dir", type=Path, default=REPO / "logs")
    parser.add_argument("--max-steps", type=int, default=20000)
    return parser.parse_args(argv)


def main(argv=None):
    in_stream, out_stream = claim_stdio()
    args = parse_args(argv)
    os.chdir(REPO)

    args.log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    logging.basicConfig(
        filename=args.log_dir / f"spire-random-{stamp}.log",
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        encoding="utf-8",
    )
    log = logging.getLogger("run_random")
    log.info("starting: %s", vars(args))

    recorder = None
    if args.record:
        recorder = StateRecorder(args.log_dir / f"states-{stamp}.jsonl")
        log.info("recording states to %s", recorder.path)

    try:
        result = play_one_run(
            Connection(in_stream, out_stream, recorder),
            RandomPlayer(),
            character=args.character,
            ascension=args.ascension,
            seed=args.seed,
            max_steps=args.max_steps,
        )
    except Exception:
        log.exception("random player crashed")
        return 1
    finally:
        if recorder:
            recorder.close()

    log.info("result: %s", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
