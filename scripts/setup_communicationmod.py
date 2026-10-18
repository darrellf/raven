"""Point CommunicationMod at our launcher by setting command= in its config.

Run from the repo with the venv's python:
    .venv/Scripts/python.exe scripts/setup_communicationmod.py --dry-run
    .venv/Scripts/python.exe scripts/setup_communicationmod.py --record

Other settings in the file are kept. A backup is saved next to it as
config.properties.bak. This script doesn't run under the game, so it prints.
"""

import argparse
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from raven.games.spire.config import (  # noqa: E402
    build_command,
    default_config_path,
    update_config_text,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--record", action="store_true", help="save raw game states")
    parser.add_argument("--seed", default=None)
    parser.add_argument("--dry-run", action="store_true", help="show the change only")
    args = parser.parse_args(argv)

    config = args.config or default_config_path()
    python = REPO / ".venv" / "Scripts" / "python.exe"
    script = REPO / "scripts" / "run_random.py"
    if not python.exists():
        print(f"No venv python at {python}. Create the venv first.")
        return 1

    extra = []
    if args.record:
        extra.append("--record")
    if args.seed:
        extra += ["--seed", args.seed]
    try:
        command = build_command(python, script, extra)
    except ValueError as error:
        print(error)
        return 1

    old_text = config.read_text(encoding="utf-8") if config.exists() else ""
    new_text = update_config_text(old_text, command)

    print(f"Config file: {config}")
    print(f"Command:     {command}")
    print("New file contents:")
    print(new_text)
    if args.dry_run:
        print("Dry run, nothing written.")
        return 0

    config.parent.mkdir(parents=True, exist_ok=True)
    if config.exists():
        shutil.copy2(config, config.with_name(config.name + ".bak"))
    config.write_text(new_text, encoding="utf-8")
    print("Written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
