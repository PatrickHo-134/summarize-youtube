import os
import json
import pytest
from unittest.mock import patch, MagicMock

os.environ['AWS_DEFAULT_REGION'] = 'ap-southeast-2'
os.environ['USER_SUBMISSIONS_TABLE'] = 'user-submissions'
os.environ['YOUTUBE_SUMMARIES_TABLE'] = 'youtube-summaries'

with patch('boto3.resource'), patch('boto3.client'):
    from src.lambda_function import lambda_handler

AUTHED_EVENT = {
    'httpMethod': 'GET',
    'requestContext': {
        'authorizer': {
            'claims': {
                'sub': 'test-user-abc'
            }
        }
    }
}

UNAUTHED_EVENT = {
    'httpMethod': 'GET',
    'requestContext': {
        'authorizer': {
            'claims': {}
        }
    }
}

OPTIONS_EVENT = {
    'httpMethod': 'OPTIONS',
    'requestContext': {},
}


# ---------------------------------------------------------------------------
# Unauthorized
# ---------------------------------------------------------------------------

def test_missing_sub_returns_401():
    response = lambda_handler(UNAUTHED_EVENT, {})
    assert response['statusCode'] == 401
    body = json.loads(response['body'])
    assert 'Unauthorized' in body['error']


# ---------------------------------------------------------------------------
# CORS preflight
# ---------------------------------------------------------------------------

def test_options_preflight_returns_200():
    response = lambda_handler(OPTIONS_EVENT, {})
    assert response['statusCode'] == 200
    assert 'Access-Control-Allow-Origin' in response['headers']
    assert 'Access-Control-Allow-Methods' in response['headers']
    assert 'Access-Control-Allow-Headers' in response['headers']


# ---------------------------------------------------------------------------
# Empty history
# ---------------------------------------------------------------------------

@patch('src.lambda_function.get_submissions')
def test_empty_submissions_returns_empty_items(mock_get_submissions):
    mock_get_submissions.return_value = []

    response = lambda_handler(AUTHED_EVENT, {})

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body == {'items': []}
    mock_get_submissions.assert_called_once_with('test-user-abc')


# ---------------------------------------------------------------------------
# Successful multi-item history retrieval
# ---------------------------------------------------------------------------

@patch('src.lambda_function.batch_get_summaries')
@patch('src.lambda_function.get_submissions')
def test_successful_history_retrieval(mock_get_submissions, mock_batch_get):
    mock_get_submissions.return_value = [
        {'user_id': 'test-user-abc', 'video_id': 'vid111', 'created_at': '2026-09-10T10:00:00Z'},
        {'user_id': 'test-user-abc', 'video_id': 'vid222', 'created_at': '2026-09-12T15:30:00Z'},
    ]
    mock_batch_get.return_value = {
        'vid111': {'title': 'First Video', 'summary': 'Summary of first video.'},
        'vid222': {'title': 'Second Video', 'summary': 'Summary of second video.'},
    }

    response = lambda_handler(AUTHED_EVENT, {})

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    items = body['items']

    assert len(items) == 2
    assert 'Access-Control-Allow-Origin' in response['headers']

    by_id = {item['videoId']: item for item in items}

    assert by_id['vid111']['title'] == 'First Video'
    assert by_id['vid111']['summary'] == 'Summary of first video.'
    assert by_id['vid111']['videoUrl'] == 'https://www.youtube.com/watch?v=vid111'
    assert by_id['vid111']['createdAt'] == '2026-09-10T10:00:00Z'

    assert by_id['vid222']['title'] == 'Second Video'
    assert by_id['vid222']['videoUrl'] == 'https://www.youtube.com/watch?v=vid222'

    mock_get_submissions.assert_called_once_with('test-user-abc')
    mock_batch_get.assert_called_once_with(['vid111', 'vid222'])


@patch('src.lambda_function.batch_get_summaries')
@patch('src.lambda_function.get_submissions')
def test_history_returned_newest_first(mock_get_submissions, mock_batch_get):
    mock_get_submissions.return_value = [
        {'user_id': 'test-user-abc', 'video_id': 'old_vid', 'created_at': '2026-01-01T00:00:00Z'},
        {'user_id': 'test-user-abc', 'video_id': 'new_vid', 'created_at': '2026-09-01T00:00:00Z'},
    ]
    mock_batch_get.return_value = {
        'old_vid': {'title': 'Old', 'summary': 'Old summary.'},
        'new_vid': {'title': 'New', 'summary': 'New summary.'},
    }

    response = lambda_handler(AUTHED_EVENT, {})
    items = json.loads(response['body'])['items']

    assert items[0]['videoId'] == 'new_vid'
    assert items[1]['videoId'] == 'old_vid'


@patch('src.lambda_function.batch_get_summaries')
@patch('src.lambda_function.get_submissions')
def test_missing_summary_data_defaults_to_empty_strings(mock_get_submissions, mock_batch_get):
    mock_get_submissions.return_value = [
        {'user_id': 'test-user-abc', 'video_id': 'orphan_vid', 'created_at': '2026-09-01T00:00:00Z'},
    ]
    mock_batch_get.return_value = {}

    response = lambda_handler(AUTHED_EVENT, {})
    items = json.loads(response['body'])['items']

    assert len(items) == 1
    assert items[0]['videoId'] == 'orphan_vid'
    assert items[0]['title'] == ''
    assert items[0]['summary'] == ''
