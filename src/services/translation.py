import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = "https://genai.comp.polyu.edu.hk/api/v1/chat/completions"
MODEL = "DeepSeek-V4-Flash"
API_KEY_ENV = "COMP_GENAI_API_KEY"
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


def _prompt(title: str, content: str, language: str, operation: str) -> str:
    language_name = SUPPORTED_LANGUAGES[language]
    if operation == "rewrite":
        instruction = (
            f"Translate and naturally polish the note into {language_name}. Preserve the meaning, "
            "improve clarity and flow, and do not add facts."
        )
    else:
        instruction = f"Translate the note accurately into {language_name}. Preserve its meaning and tone."

    return (
        f"{instruction}\n"
        "Return only a valid JSON object with exactly two string fields: title and content. "
        "Do not wrap the JSON in Markdown fences.\n\n"
        f"Title:\n{title}\n\nContent:\n{content}"
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
        "model": MODEL,
        "messages": [{"role": "user", "content": _prompt(title, content, language, operation)}],
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
        raise TranslationError("Could not reach the translation API. Check the network or approved VPN connection.") from error
    except json.JSONDecodeError as error:
        raise TranslationError("The translation API returned invalid JSON.") from error

    try:
        raw_content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise TranslationError("The translation API response did not contain an assistant answer.") from error

    return _parse_result(raw_content)
