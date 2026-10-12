import os


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing mandatory environment variable: '{name}'")
    return value


def _optional(name: str, default: str = "") -> str:
    return os.environ.get(name, default)

# these configs are stored in lambda environment variables
SUMMARIZATION_JOBS_TABLE: str = _require("SUMMARIZATION_JOBS_TABLE")
YOUTUBE_SUMMARIES_TABLE: str = _require("YOUTUBE_SUMMARIES_TABLE")
SQS_QUEUE_URL: str = _require("SQS_QUEUE_URL")