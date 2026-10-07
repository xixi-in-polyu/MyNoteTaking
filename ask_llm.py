#!/usr/bin/env python3
"""Ask the COMP on-premises GenAI endpoint a question."""

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "https://genai.comp.polyu.edu.hk/api/v1/chat/completions"
MODEL = "DeepSeek-V4-Flash"
API_KEY_ENV = "COMP_GENAI_API_KEY"


def load_dotenv() -> None:
    """Load simple KEY=VALUE entries from a local .env file."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(env_path, encoding="utf-8") as env_file:
            for line in env_file:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                value = value.strip().strip("\"'")
                os.environ.setdefault(name.strip(), value)
    except FileNotFoundError:
        pass


def ask_llm(question: str, api_key: str) -> str:
    """Send one question to the configured chat-completions endpoint."""
    request_body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": question}],
        "stream": False,
    }
    request = Request(
        API_URL,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            f"The API returned HTTP {error.code}. {detail or 'No error details.'}"
        ) from error
    except URLError as error:
        raise RuntimeError(
            "Could not reach the API. Connect to the PolyU campus network "
            "or its approved VPN and try again."
        ) from error
    except json.JSONDecodeError as error:
        raise RuntimeError("The API returned an invalid JSON response.") from error

    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError("The API response did not contain an assistant answer.") from error


def main() -> int:
    load_dotenv()
    api_key = os.environ.get(API_KEY_ENV, "").strip()
    if not api_key:
        print(
            f"Missing API key. Set it in the {API_KEY_ENV} environment variable.",
            file=sys.stderr,
        )
        return 1

    question = input("Question (or type 'exit' to quit): ").strip()
    if not question or question.lower() == "exit":
        return 0

    try:
        answer = ask_llm(question, api_key)
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"\n{answer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())