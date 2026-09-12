import os
import json
import pytest
from unittest.mock import patch

os.environ["AWS_DEFAULT_REGION"] = "ap-southeast-2"
os.environ["DYNAMODB_TABLE"] = "youtube-summaries"
os.environ["SSM_PARAM_NAME"] = "/dummy/path"

with patch('boto3.client'), patch('boto3.resource'):
    from src.lambda_function import (
        extract_and_validate_video_id,
        lambda_handler,
        get_transcript
    )
    from youtube_transcript_api._errors import TranscriptsDisabled

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
