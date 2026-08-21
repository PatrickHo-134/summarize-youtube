import os
import json
import pytest
from unittest.mock import patch

# 1. Set environment variables BEFORE importing the lambda function.
# This ensures boto3 doesn't look for real AWS credentials during tests.
os.environ["AWS_DEFAULT_REGION"] = "ap-southeast-2" # Match your Sydney region
os.environ["DYNAMODB_TABLE"] = "youtube-summaries"
os.environ["SSM_PARAM_NAME"] = "/dummy/path"

# 2. Mock the boto3 client creation to prevent AWS connection attempts on load
with patch('boto3.client'), patch('boto3.resource'):
    from src.lambda_function import (
        extract_and_validate_video_id,
        lambda_handler,
        get_transcript
    )
    from youtube_transcript_api._errors import TranscriptsDisabled

# --- TEST 1: URL Validation (Regex) ---
def test_extract_and_validate_video_id():
    # Valid URLs
    assert extract_and_validate_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_and_validate_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_and_validate_video_id("https://youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    # Invalid URLs
    assert extract_and_validate_video_id("https://google.com") is None
    assert extract_and_validate_video_id("not-a-url") is None
    assert extract_and_validate_video_id("") is None

def test_lambda_handler_invalid_url():
    event = {"body": json.dumps({"url": "https://google.com"})}
    response = lambda_handler(event, {})

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "Invalid or missing YouTube URL" in body["error"]

# --- TEST 2: DynamoDB Cache Hit (Bypasses LLM and Transcript) ---
@patch('src.lambda_function.check_cache')
def test_lambda_handler_cache_hit(mock_check_cache):
    # Simulate finding the summary in DynamoDB
    mock_check_cache.return_value = "- Cached Point 1\n- Cached Point 2"

    event = {"body": json.dumps({"url": "https://youtube.com/watch?v=12345678901"})}
    response = lambda_handler(event, {})

    assert response["statusCode"] == 200
    body = json.loads(response["body"])

    assert body["summary"] == "- Cached Point 1\n- Cached Point 2"
    assert body["source"] == "cache" # Validates it came from DB
    mock_check_cache.assert_called_once_with("12345678901")

# --- TEST 3: Full Flow (Cache Miss, Fetch Transcript, Call LLM, Save Cache) ---
@patch('src.lambda_function.check_cache')
@patch('src.lambda_function.get_transcript')
@patch('src.lambda_function.summarise')
@patch('src.lambda_function.save_to_cache')
def test_lambda_handler_cache_miss_success(mock_save, mock_summarise, mock_get_transcript, mock_check_cache):
    # Simulate DB miss
    mock_check_cache.return_value = None

    # Simulate successful transcript fetch
    mock_get_transcript.return_value = ("Full transcript content", None)

    # Simulate successful OpenAI call
    mock_summarise.return_value = ("New AI summary", None)

    event = {"body": json.dumps({"url": "https://youtube.com/watch?v=12345678901"})}
    response = lambda_handler(event, {})

    assert response["statusCode"] == 200
    body = json.loads(response["body"])

    assert body["summary"] == "New AI summary"
    assert body["source"] == "llm"

    # Verify the sequence of function calls
    mock_check_cache.assert_called_once_with("12345678901")
    mock_get_transcript.assert_called_once_with("12345678901")
    mock_summarise.assert_called_once_with("Full transcript content")
    mock_save.assert_called_once_with("12345678901", "New AI summary")

# --- TEST 4: Transcript Failure (e.g., Subtitles Disabled) ---
@patch('src.lambda_function.check_cache')
@patch('src.lambda_function.YouTubeTranscriptApi')
def test_lambda_handler_transcript_disabled(mock_ytt, mock_check_cache):
    mock_check_cache.return_value = None

    # Simulate the YouTube API throwing a TranscriptsDisabled error
    mock_ytt.get_transcript.side_effect = TranscriptsDisabled("12345678901")

    event = {"body": json.dumps({"url": "https://youtube.com/watch?v=12345678901"})}
    response = lambda_handler(event, {})

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "Could not retrieve a transcript" in body["error"]