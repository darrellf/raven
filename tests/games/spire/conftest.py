import copy
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.fixture
def state():
    """Load a sample state by name; each call returns a fresh copy."""
    return lambda name: copy.deepcopy(load_fixture(name))
