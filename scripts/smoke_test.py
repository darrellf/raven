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
            "max_tokens": 50,
        },
        timeout=30,
    )
    if not response.ok:
        print(f"Request failed: HTTP {response.status_code}")
        print(response.text)
        return 1

    data = response.json()
    usage = data.get("usage", {})
    print(f"Model: {data.get('model')}")
    print(f"Reply: {data['choices'][0]['message']['content']}")
    print(
        f"Tokens: prompt={usage.get('prompt_tokens')} "
        f"completion={usage.get('completion_tokens')} "
        f"total={usage.get('total_tokens')}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
