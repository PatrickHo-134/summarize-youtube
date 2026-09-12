import os
import json
import pytest
from unittest.mock import patch, MagicMock
import httpx2

os.environ["AWS_DEFAULT_REGION"] = "ap-southeast-2"
os.environ["DYNAMODB_TABLE"] = "youtube-summaries"
os.environ["SSM_PARAM_NAME"] = "/dummy/path"

with patch('boto3.client'), patch('boto3.resource'):
    from src.lambda_function import (
        extract_and_validate_video_id,
        lambda_handler,
        get_transcript,
        summarise,
    )
    from youtube_transcript_api._errors import TranscriptsDisabled, VideoUnavailable, NoTranscriptFound
    from openai import RateLimitError, APITimeoutError, BadRequestError


def make_openai_response(status_code=429):
    mock_response = MagicMock()
    mock_response.headers = {'x-request-id': 'test-id'}
    mock_response.status_code = status_code
    return mock_response

AUTHED_EVENT_BASE = {
    "requestContext": {
        "authorizer": {
            "claims": {
                "sub": "test-user-123"
            }
        }
    }
}

def make_event(url):
    return {**AUTHED_EVENT_BASE, "body": json.dumps({"url": url})}


def test_extract_and_validate_video_id():
    assert extract_and_validate_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_and_validate_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_and_validate_video_id("https://youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    assert extract_and_validate_video_id("https://google.com") is None
    assert extract_and_validate_video_id("not-a-url") is None
    assert extract_and_validate_video_id("") is None


@patch('src.lambda_function.record_user_submission')
def test_lambda_handler_invalid_url(mock_record):
    event = {**AUTHED_EVENT_BASE, "body": json.dumps({"url": "https://google.com"})}
    response = lambda_handler(event, {})

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "Invalid or missing YouTube URL" in body["error"]


@patch('src.lambda_function.record_user_submission')
@patch('src.lambda_function.check_cache')
def test_lambda_handler_cache_hit(mock_check_cache, mock_record):
    mock_check_cache.return_value = "- Cached Point 1\n- Cached Point 2"

    response = lambda_handler(make_event("https://youtube.com/watch?v=12345678901"), {})

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["summary"] == "- Cached Point 1\n- Cached Point 2"
    assert body["source"] == "cache"
    mock_check_cache.assert_called_once_with("12345678901")


@patch('src.lambda_function.record_user_submission')
@patch('src.lambda_function.check_cache')
@patch('src.lambda_function.get_transcript')
@patch('src.lambda_function.summarise')
@patch('src.lambda_function.save_to_cache')
def test_lambda_handler_cache_miss_success(mock_save, mock_summarise, mock_get_transcript, mock_check_cache, mock_record):
    mock_check_cache.return_value = None
    mock_get_transcript.return_value = ("Full transcript content", None, None)
    mock_summarise.return_value = ("New AI summary", None, None)

    response = lambda_handler(make_event("https://youtube.com/watch?v=12345678901"), {})

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["summary"] == "New AI summary"
    assert body["source"] == "llm"

    mock_check_cache.assert_called_once_with("12345678901")
    mock_get_transcript.assert_called_once_with("12345678901")
    mock_summarise.assert_called_once_with("Full transcript content")
    mock_save.assert_called_once_with("12345678901", "New AI summary")


@patch('src.lambda_function.record_user_submission')
@patch('src.lambda_function.check_cache')
@patch('src.lambda_function.get_transcript')
def test_lambda_handler_transcript_disabled(mock_get_transcript, mock_check_cache, mock_record):
    mock_check_cache.return_value = None
    mock_get_transcript.return_value = (None, "Transcripts are disabled for this video.", 400)

    response = lambda_handler(make_event("https://youtube.com/watch?v=12345678901"), {})

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "Transcripts are disabled" in body["error"]


# --- YouTube Exception Tests (get_transcript isolation) ---

@patch('src.lambda_function.YouTubeTranscriptApi')
def test_get_transcript_video_unavailable(mock_ytt_class):
    mock_ytt_class.return_value.fetch.side_effect = VideoUnavailable("abc123")

    content, error, status = get_transcript("abc123")

    assert content is None
    assert status == 400
    assert "unavailable" in error.lower()


@patch('src.lambda_function.YouTubeTranscriptApi')
def test_get_transcript_transcripts_disabled(mock_ytt_class):
    mock_ytt_class.return_value.fetch.side_effect = TranscriptsDisabled("abc123")

    content, error, status = get_transcript("abc123")

    assert content is None
    assert status == 400
    assert "disabled" in error.lower()


@patch('src.lambda_function.YouTubeTranscriptApi')
def test_get_transcript_no_transcript_found(mock_ytt_class):
    mock_ytt_class.return_value.fetch.side_effect = NoTranscriptFound("abc123", [], {})

    content, error, status = get_transcript("abc123")

    assert content is None
    assert status == 400
    assert "no transcript" in error.lower()


@patch('src.lambda_function.time.sleep')
@patch('src.lambda_function.YouTubeTranscriptApi')
def test_get_transcript_all_proxies_exhausted(mock_ytt_class, mock_sleep):
    mock_ytt_class.return_value.fetch.side_effect = Exception("Connection refused")

    with patch.dict(os.environ, {"PROXY_POOL_URLS": "http://proxy1:8080,http://proxy2:8080"}):
        content, error, status = get_transcript("abc123")

    assert content is None
    assert status == 429
    assert "proxies exhausted" in error.lower()
    assert mock_sleep.call_count == 1


@patch('src.lambda_function.time.sleep')
@patch('src.lambda_function.YouTubeTranscriptApi')
def test_get_transcript_succeeds_on_second_proxy(mock_ytt_class, mock_sleep):
    failing_instance = MagicMock()
    failing_instance.fetch.side_effect = Exception("429 Too Many Requests")

    success_instance = MagicMock()
    transcript_snippet = MagicMock()
    transcript_snippet.__getitem__ = lambda self, key: "Hello world" if key == "text" else None
    success_instance.fetch.return_value.to_raw_data.return_value = [{"text": "Hello world"}]

    mock_ytt_class.side_effect = [failing_instance, success_instance]

    with patch.dict(os.environ, {"PROXY_POOL_URLS": "http://proxy1:8080,http://proxy2:8080"}):
        content, error, status = get_transcript("abc123")

    assert error is None
    assert status is None
    assert content == "Hello world"
    assert mock_sleep.call_count == 1


@patch('src.lambda_function.time.sleep')
@patch('src.lambda_function.YouTubeTranscriptApi')
def test_get_transcript_retries_all_proxies_before_exhaustion(mock_ytt_class, mock_sleep):
    mock_ytt_class.return_value.fetch.side_effect = Exception("Blocked")

    pool = "http://p1:8080,http://p2:8080,http://p3:8080"
    with patch.dict(os.environ, {"PROXY_POOL_URLS": pool}):
        content, error, status = get_transcript("abc123")

    assert status == 429
    assert mock_ytt_class.call_count == 3
    assert mock_sleep.call_count == 2


@patch('src.lambda_function.time.sleep')
@patch('src.lambda_function.YouTubeTranscriptApi')
def test_get_transcript_no_sleep_on_first_attempt(mock_ytt_class, mock_sleep):
    mock_ytt_class.return_value.fetch.side_effect = Exception("Blocked")

    with patch.dict(os.environ, {"PROXY_POOL_URLS": "http://proxy1:8080"}):
        get_transcript("abc123")

    mock_sleep.assert_not_called()


@patch('src.lambda_function.record_user_submission')
@patch('src.lambda_function.check_cache')
@patch('src.lambda_function.time.sleep')
@patch('src.lambda_function.YouTubeTranscriptApi')
def test_lambda_handler_all_proxies_fail_returns_429(mock_ytt_class, mock_sleep, mock_check_cache, mock_record):
    mock_check_cache.return_value = None
    mock_ytt_class.return_value.fetch.side_effect = Exception("Connection refused")

    pool = "http://p1:8080,http://p2:8080"
    with patch.dict(os.environ, {"PROXY_POOL_URLS": pool}):
        response = lambda_handler(make_event("https://youtube.com/watch?v=12345678901"), {})

    assert response["statusCode"] == 429
    body = json.loads(response["body"])
    assert "proxies exhausted" in body["error"].lower()
    assert mock_ytt_class.call_count == 2
    assert mock_sleep.call_count == 1


@patch('src.lambda_function.time.sleep')
@patch('src.lambda_function.YouTubeTranscriptApi')
def test_non_retryable_error_bypasses_proxy_rotation(mock_ytt_class, mock_sleep):
    proxy1_instance = MagicMock()
    proxy1_instance.fetch.side_effect = VideoUnavailable("abc123")
    proxy2_instance = MagicMock()
    mock_ytt_class.side_effect = [proxy1_instance, proxy2_instance]

    pool = "http://p1:8080,http://p2:8080"
    with patch.dict(os.environ, {"PROXY_POOL_URLS": pool}):
        content, error, status = get_transcript("abc123")

    assert content is None
    assert status == 400
    assert "unavailable" in error.lower()
    assert mock_ytt_class.call_count == 1
    proxy2_instance.fetch.assert_not_called()
    mock_sleep.assert_not_called()


# --- OpenAI Exception Tests (summarise isolation) ---

@patch('src.lambda_function.get_openai_client')
def test_summarise_rate_limit_error(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RateLimitError(
        "rate limit exceeded", response=make_openai_response(429), body=None
    )
    mock_get_client.return_value = mock_client

    result, error, status = summarise("some transcript")

    assert result is None
    assert status == 429
    assert "rate limit" in error.lower()


@patch('src.lambda_function.get_openai_client')
def test_summarise_timeout_error(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = APITimeoutError(
        request=MagicMock(spec=httpx2.Request)
    )
    mock_get_client.return_value = mock_client

    result, error, status = summarise("some transcript")

    assert result is None
    assert status == 504
    assert "timed out" in error.lower()


@patch('src.lambda_function.get_openai_client')
def test_summarise_context_length_exceeded(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = BadRequestError(
        "context_length_exceeded: max tokens", response=make_openai_response(400), body=None
    )
    mock_get_client.return_value = mock_client

    result, error, status = summarise("some transcript")

    assert result is None
    assert status == 400
    assert "too long" in error.lower()


@patch('src.lambda_function.get_openai_client')
def test_summarise_bad_request_other(mock_get_client):
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = BadRequestError(
        "invalid model", response=make_openai_response(400), body=None
    )
    mock_get_client.return_value = mock_client

    result, error, status = summarise("some transcript")

    assert result is None
    assert status == 400
    assert "OpenAI rejected" in error


# --- HTTP Status Code Mapping (lambda_handler integration) ---

@patch('src.lambda_function.record_user_submission')
@patch('src.lambda_function.check_cache')
@patch('src.lambda_function.get_transcript')
@patch('src.lambda_function.summarise')
def test_lambda_handler_openai_rate_limit_returns_429(mock_summarise, mock_get_transcript, mock_check_cache, mock_record):
    mock_check_cache.return_value = None
    mock_get_transcript.return_value = ("transcript", None, None)
    mock_summarise.return_value = (None, "OpenAI rate limit reached. Please try again in a moment.", 429)

    response = lambda_handler(make_event("https://youtube.com/watch?v=12345678901"), {})

    assert response["statusCode"] == 429


@patch('src.lambda_function.record_user_submission')
@patch('src.lambda_function.check_cache')
@patch('src.lambda_function.get_transcript')
@patch('src.lambda_function.summarise')
def test_lambda_handler_openai_timeout_returns_504(mock_summarise, mock_get_transcript, mock_check_cache, mock_record):
    mock_check_cache.return_value = None
    mock_get_transcript.return_value = ("transcript", None, None)
    mock_summarise.return_value = (None, "OpenAI request timed out. Please try again.", 504)

    response = lambda_handler(make_event("https://youtube.com/watch?v=12345678901"), {})

    assert response["statusCode"] == 504


@patch('src.lambda_function.record_user_submission')
@patch('src.lambda_function.check_cache')
@patch('src.lambda_function.get_transcript')
@patch('src.lambda_function.summarise')
def test_lambda_handler_transcript_too_long_returns_400(mock_summarise, mock_get_transcript, mock_check_cache, mock_record):
    mock_check_cache.return_value = None
    mock_get_transcript.return_value = ("transcript", None, None)
    mock_summarise.return_value = (None, "This video's transcript is too long to summarize.", 400)

    response = lambda_handler(make_event("https://youtube.com/watch?v=12345678901"), {})

    assert response["statusCode"] == 400
