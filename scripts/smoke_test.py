"""Manual smoke test: send one short message to mistral-large-4.

Run from the repo root with the venv active:
    python scripts/smoke_test.py

Needs MISTRAL_API_KEY in .env. Not part of the test suite, and not run
under the game, so printing to stdout is fine here.
"""

import os
import sys

import requests
from dotenv import load_dotenv

API_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL = "mistral-large-4"
# The model thinks before answering, and thinking counts toward this limit.
MAX_TOKENS = 1000


def split_content(content):
    """Return (thinking, answer) text from a message's content.

    Content is a plain string when the model doesn't think, or a list of
    chunks: {"type": "thinking", "thinking": [text chunks]} and
    {"type": "text", "text": ...}.
    """
    if content is None:
        return "", ""
    if isinstance(content, str):
        return "", content

    thinking, answer = [], []
    for chunk in content:
        if chunk.get("type") == "thinking":
            for part in chunk.get("thinking", []):
                if part.get("type") == "text":
                    thinking.append(part.get("text", ""))
        elif chunk.get("type") == "text":
            answer.append(chunk.get("text", ""))
    return "".join(thinking), "".join(answer)


def usage_lines(usage):
    """Format token usage, with thinking split out when the API reports it."""
    completion = usage.get("completion_tokens")
    details = usage.get("completion_tokens_details") or {}
    reasoning = details.get("reasoning_tokens")

    lines = [f"  prompt:     {usage.get('prompt_tokens')}"]
    if reasoning is not None and completion is not None:
        lines.append(f"  thinking:   {reasoning}")
        lines.append(f"  answer:     {completion - reasoning}")
    else:
        lines.append(f"  completion: {completion} (no thinking breakdown reported)")
    lines.append(f"  total:      {usage.get('total_tokens')}")
    return lines


def main() -> int:
    load_dotenv()
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key or api_key == "your-key-here":
        print("MISTRAL_API_KEY is not set. Copy .env.example to .env and add your key.")
        return 1

    response = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": "Say hi in one short sentence."}],
            "max_tokens": MAX_TOKENS,
        },
        timeout=60,
    )
    if not response.ok:
        print(f"Request failed: HTTP {response.status_code}")
        print(response.text)
        return 1

    data = response.json()
    choice = data["choices"][0]
    thinking, answer = split_content(choice["message"].get("content"))

    print(f"Model: {data.get('model')}")
    print(f"Finish reason: {choice.get('finish_reason')}")
    print("Thinking:")
    print(f"  {thinking.strip() or '(none)'}")
    print("Answer:")
    print(f"  {answer.strip() or '(none)'}")
    print("Tokens:")
    for line in usage_lines(data.get("usage", {})):
        print(line)
    if choice.get("finish_reason") == "length":
        print(f"Warning: hit max_tokens ({MAX_TOKENS}) before finishing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
