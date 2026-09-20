import os


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing mandatory environment variable: '{name}'")
    return value


def _optional(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


YOUTUBE_SUMMARIES_TABLE: str = _optional("DYNAMODB_TABLE", "youtube-summaries")
USER_SUBMISSIONS_TABLE: str = _optional("USER_SUBMISSIONS_TABLE", "user-submissions")
CORS_ALLOW_ORIGIN: str = _optional("CORS_ALLOW_ORIGIN", "*")
LLM_MODEL: str = _optional("LLM_MODEL", "gpt-4o-mini")
LLM_MAX_TOKENS: int = int(_optional("LLM_MAX_TOKENS", "1000"))
LLM_TEMPERATURE: float = float(_optional("LLM_TEMPERATURE", "0.7"))
# these configs are stored in lambda environment variables
PROXY_POOL_URLS: str = _optional("PROXY_POOL_URLS") or _optional("PROXY_URL")
SSM_PARAM_NAME: str = _require("SSM_PARAM_NAME")
TRANSCRIPT_BUCKET: str = _optional("TRANSCRIPT_BUCKET")