import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openrouter/free"
API_KEY_ENV = "OPENROUTER_API_KEY"
PROMPT_FILE = Path(__file__).resolve().parents[2] / "prompt" / "note-translation.prompt.md"
SUPPORTED_LANGUAGES = {
    "en": "English",
    "zh-CN": "Simplified Chinese",
    "zh-TW": "Traditional Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
}


class TranslationError(RuntimeError):
    """Raised when the translation provider cannot produce valid output."""


def _load_dotenv() -> None:
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    try:
        with open(env_path, encoding="utf-8") as env_file:
            for line in env_file:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                os.environ.setdefault(name.strip(), value.strip().strip("\"'"))
    except FileNotFoundError:
        pass


def _api_key() -> str:
    _load_dotenv()
    api_key = os.environ.get(API_KEY_ENV, "").strip()
    if not api_key:
        raise TranslationError(f"Missing {API_KEY_ENV} configuration.")
    return api_key


def _model() -> str:
    """Allow deployments to pin a specific OpenRouter model without a code change."""
    return os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _prompt(language: str, operation: str) -> str:
    language_name = SUPPORTED_LANGUAGES[language]
    if operation == "rewrite":
        operation_instruction = (
            "Translate and naturally polish the note. Improve clarity and flow without changing "
            "its meaning or adding facts."
        )
    else:
        operation_instruction = "Translate the note accurately, preserving its meaning and tone."

    try:
        template = PROMPT_FILE.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise TranslationError(f"Could not load the translation prompt from {PROMPT_FILE}.") from error

    required_placeholders = ("{{language}}", "{{operation_instruction}}")
    if any(placeholder not in template for placeholder in required_placeholders):
        raise TranslationError(f"The translation prompt at {PROMPT_FILE} is missing required placeholders.")

    return (
        template.replace("{{language}}", language_name)
        .replace("{{operation_instruction}}", operation_instruction)
    )


def _parse_result(raw_content: object) -> dict[str, str]:
    if not isinstance(raw_content, str):
        raise TranslationError("The API response contained an invalid assistant answer.")

    cleaned = raw_content.strip()
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1]).strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise TranslationError("The API returned invalid translation JSON.") from error

    if not isinstance(result, dict) or not isinstance(result.get("title"), str) or not isinstance(result.get("content"), str):
        raise TranslationError("The API response must contain string title and content fields.")

    return {"title": result["title"], "content": result["content"]}


def generate_note_output(title: str, content: str, language: str, operation: str) -> dict[str, str]:
    if language not in SUPPORTED_LANGUAGES:
        raise TranslationError("Unsupported target language.")
    if operation not in {"translate", "rewrite"}:
        raise TranslationError("Unsupported note operation.")

    request_body = {
        "model": _model(),
        "messages": [
            {"role": "system", "content": _prompt(language, operation)},
            {
                "role": "user",
                "content": json.dumps(
                    {"title": title, "content": content},
                    ensure_ascii=False,
                ),
            },
        ],
        "stream": False,
    }
    request = Request(
        API_URL,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {_api_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace").strip()
        raise TranslationError(f"The translation API returned HTTP {error.code}. {detail or 'No details.'}") from error
    except URLError as error:
        raise TranslationError("Could not reach OpenRouter. Check the server network connection.") from error
    except json.JSONDecodeError as error:
        raise TranslationError("The translation API returned invalid JSON.") from error

    try:
        raw_content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise TranslationError("The translation API response did not contain an assistant answer.") from error

    return _parse_result(raw_content)
