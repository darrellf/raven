import pytest

from raven.games.spire.config import build_command, escape_value, update_config_text


def test_escape_backslashes_and_colons():
    assert escape_value(r"D:\dev\raven") == r"D\:\\dev\\raven"


def test_build_command_joins_parts():
    command = build_command(r"D:\py.exe", r"D:\run.py", ["--record"])
    assert command == r"D:\py.exe D:\run.py --record"


def test_build_command_rejects_spaces():
    with pytest.raises(ValueError):
        build_command(r"C:\Program Files\py.exe", r"D:\run.py")


def test_update_replaces_existing_command_and_keeps_other_lines():
    text = "#Fri Oct 17\nverbose=true\ncommand=old\nrunAtGameStart=false\n"
    new = update_config_text(text, r"D:\py.exe D:\run.py")
    assert new == (
        "#Fri Oct 17\nverbose=true\n"
        r"command=D\:\\py.exe D\:\\run.py" "\nrunAtGameStart=false\n"
    )


def test_update_adds_command_to_empty_file():
    assert update_config_text("", "py run.py") == "command=py run.py\n"
