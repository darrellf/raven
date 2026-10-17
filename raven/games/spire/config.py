"""Writing CommunicationMod's config.properties so the game launches our code.

The file is a Java properties file, so `\\` and `:` in the value must be
escaped. CommunicationMod splits the command on spaces, so paths with spaces
can't be used.
"""

import os
from pathlib import Path


def default_config_path():
    return (
        Path(os.environ["LOCALAPPDATA"])
        / "ModTheSpire"
        / "CommunicationMod"
        / "config.properties"
    )


def escape_value(value):
    """Escape a value for a properties file: `\\` -> `\\\\`, `:` -> `\\:`."""
    return value.replace("\\", "\\\\").replace(":", "\\:")


def build_command(python, script, args=()):
    """The command the game runs, unescaped. Rejects parts containing spaces."""
    parts = [str(python), str(script), *args]
    for part in parts:
        if " " in part:
            raise ValueError(
                f"CommunicationMod splits the command on spaces, so this won't work: {part}"
            )
    return " ".join(parts)


def update_config_text(text, command):
    """Return `text` with its command= line set to `command`, keeping other lines."""
    line = "command=" + escape_value(command)
    lines = text.splitlines()
    for i, existing in enumerate(lines):
        if existing.lstrip().startswith("command="):
            lines[i] = line
            break
    else:
        lines.append(line)
    return "\n".join(lines) + "\n"
