import os


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing mandatory environment variable: '{name}'")
    return value


def _optional(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


SUMMARIZATION_JOBS_TABLE = _optional('SUMMARIZATION_JOBS_TABLE', 'summarization-jobs')
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': '*',
    'Access-Control-Allow-Methods': 'OPTIONS,GET',
}
