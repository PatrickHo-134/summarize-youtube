import os
import json
import pytest
from unittest.mock import patch, MagicMock

# 1. Set dummy environment variables BEFORE importing your script
# This prevents the OpenAI client from crashing due to missing keys during tests.
os.environ["OPENAI_API_KEY"] = "dummy_key"
os.environ["OPENAI_ORG_ID"] = "dummy_org"
os.environ["OPENAI_PROJECT_ID"] = "dummy_proj"

# Now we can safely import your functions
from src.lambda_function import format_prompt_v2, get_transcript, summarise, lambda_handler
from youtube_transcript_api._errors import TranscriptsDisabled

# --- TEST 1: Pure Function Test ---
def test_format_prompt_v2():
    transcript = "This is a test transcript."
    prompt = format_prompt_v2(transcript)
    assert "This is a test transcript." in prompt
    assert "logically by theme or topic" in prompt

# --- TEST 2: YouTube API Mocking ---
@patch('src.lambda_function.YouTubeTranscriptApi.get_transcript')
def test_get_transcript_success(mock_get_transcript):
    # Setup the fake return data
    mock_get_transcript.return_value = [
        {'text': 'Hello world.'},
        {'text': 'Welcome to the video.'}
    ]

    # Run the function
    content, error = get_transcript("https://youtube.com/watch?v=12345")

    # Assertions
    assert content == "Hello world. Welcome to the video."
    assert error is None
    mock_get_transcript.assert_called_once_with("12345")

@patch('src.lambda_function.YouTubeTranscriptApi.get_transcript')
def test_get_transcript_disabled(mock_get_transcript):
    # Simulate a disabled transcript error
    mock_get_transcript.side_effect = TranscriptsDisabled("12345")

    content, error = get_transcript("https://youtube.com/watch?v=12345")

    assert content is None
    assert "Could not retrieve a transcript for the video" in error

# --- TEST 3: OpenAI API Mocking ---
@patch('src.lambda_function.client.chat.completions.create')
def test_summarise(mock_openai_create):
    # Setup a fake OpenAI response structure
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "- Fake Summary Point 1\n- Fake Summary Point 2"
    mock_openai_create.return_value = mock_response

    result = summarise("Test transcript content")

    assert "- Fake Summary Point 1" in result
    mock_openai_create.assert_called_once()

# --- TEST 4: API Gateway Lambda Handler Tests ---
@patch('src.lambda_function.get_transcript')
@patch('src.lambda_function.summarise')
def test_lambda_handler_success(mock_summarise, mock_get_transcript):
    # Mock the internal functions
    mock_get_transcript.return_value = ("Fake full transcript", None)
    mock_summarise.return_value = "Fake final summary"

    # Simulate an incoming API Gateway request
    event = {
        "body": json.dumps({"url": "https://youtube.com/watch?v=abcde"})
    }

    response = lambda_handler(event, {})

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["summary"] == "Fake final summary"

def test_lambda_handler_missing_url():
    # Simulate a bad request (empty body)
    event = {"body": "{}"}

    response = lambda_handler(event, {})

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert body["error"] == "No URL provided."