import os
import json
import pytest
from unittest.mock import patch, MagicMock

os.environ["AWS_DEFAULT_REGION"] = "ap-southeast-2"
os.environ["SUMMARIZATION_JOBS_TABLE"] = "summarization-jobs"
os.environ["YOUTUBE_SUMMARIES_TABLE"] = "youtube-summaries"
os.environ["SQS_QUEUE_URL"] = "https://sqs.ap-southeast-2.amazonaws.com/123456789/test-queue"

with patch("boto3.resource"), patch("boto3.client"):
    from src.lambda_function import handler


VIDEO_ID = "dQw4w9WgXcQ"

AUTHED_EVENT = {
    "requestContext": {
        "authorizer": {
            "claims": {
                "sub": "test-user-123"
            }
        }
    },
    "body": json.dumps({"video_id": VIDEO_ID}),
}


def make_event(body=None, claims=None):
    return {
        "requestContext": {
            "authorizer": {
                "claims": claims if claims is not None else {"sub": "test-user-123"}
            }
        },
        "body": json.dumps(body) if body is not None else json.dumps({"video_id": VIDEO_ID}),
    }


def test_missing_user_id_returns_401():
    event = make_event(claims={})
    response = handler(event, {})
    assert response["statusCode"] == 401
    assert json.loads(response["body"])["error"] == "Unauthorized"


def test_missing_video_id_returns_400():
    event = make_event(body={})
    response = handler(event, {})
    assert response["statusCode"] == 400
    assert "video_id" in json.loads(response["body"])["error"].lower()


@patch("src.lambda_function.dynamodb")
def test_cached_summary_returns_200_without_sqs(mock_dynamodb):
    mock_table = MagicMock()
    mock_table.get_item.return_value = {
        "Item": {"video_id": VIDEO_ID, "title": "Test Video", "summary": "- Point 1"}
    }
    mock_dynamodb.Table.return_value = mock_table

    response = handler(AUTHED_EVENT, {})

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "COMPLETED"
    assert body["cached"] is True
    assert body["data"]["video_id"] == VIDEO_ID


@patch("src.lambda_function.sqs")
@patch("src.lambda_function.dynamodb")
def test_uncached_creates_job_sends_sqs_returns_202(mock_dynamodb, mock_sqs):
    summaries_table = MagicMock()
    summaries_table.get_item.return_value = {}

    jobs_table = MagicMock()

    def table_selector(name):
        if name == "youtube-summaries":
            return summaries_table
        return jobs_table

    mock_dynamodb.Table.side_effect = table_selector

    response = handler(AUTHED_EVENT, {})

    assert response["statusCode"] == 202
    body = json.loads(response["body"])
    assert body["status"] == "PENDING"
    assert "job_id" in body

    job_id = body["job_id"]

    jobs_table.put_item.assert_called_once()
    put_item_arg = jobs_table.put_item.call_args[1]["Item"]
    assert put_item_arg["job_id"] == job_id
    assert put_item_arg["video_id"] == VIDEO_ID
    assert put_item_arg["user_id"] == "test-user-123"
    assert put_item_arg["status"] == "PENDING"

    mock_sqs.send_message.assert_called_once()
    sqs_body = json.loads(mock_sqs.send_message.call_args[1]["MessageBody"])
    assert sqs_body["job_id"] == job_id
    assert sqs_body["video_id"] == VIDEO_ID
    assert sqs_body["user_id"] == "test-user-123"


def test_cors_headers_present_on_all_responses():
    event = make_event(claims={})
    response = handler(event, {})
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"
    assert "Access-Control-Allow-Headers" in response["headers"]
    assert "Access-Control-Allow-Methods" in response["headers"]
