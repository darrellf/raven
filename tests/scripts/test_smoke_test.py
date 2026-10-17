import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "smoke_test.py"
spec = importlib.util.spec_from_file_location("smoke_test", SCRIPT)
smoke_test = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke_test)


def test_split_content_plain_string():
    assert smoke_test.split_content("Hi there!") == ("", "Hi there!")


def test_split_content_thinking_and_text_chunks():
    content = [
        {"type": "thinking", "thinking": [{"type": "text", "text": "They want a greeting."}]},
        {"type": "text", "text": "Hi there!"},
    ]
    assert smoke_test.split_content(content) == ("They want a greeting.", "Hi there!")


def test_split_content_thinking_only_when_cut_off():
    content = [{"type": "thinking", "thinking": [{"type": "text", "text": "I'll"}]}]
    assert smoke_test.split_content(content) == ("I'll", "")


def test_split_content_none():
    assert smoke_test.split_content(None) == ("", "")


def test_usage_lines_breaks_out_thinking():
    usage = {
        "prompt_tokens": 10,
        "completion_tokens": 450,
        "total_tokens": 460,
        "completion_tokens_details": {"reasoning_tokens": 444},
    }
    lines = smoke_test.usage_lines(usage)
    assert "  thinking:   444" in lines
    assert "  answer:     6" in lines
    assert "  total:      460" in lines


def test_usage_lines_without_breakdown():
    usage = {"prompt_tokens": 10, "completion_tokens": 3, "total_tokens": 13}
    lines = smoke_test.usage_lines(usage)
    assert "  completion: 3 (no thinking breakdown reported)" in lines
