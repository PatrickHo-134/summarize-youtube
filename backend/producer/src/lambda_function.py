import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Methods": "OPTIONS,POST",
}

dynamodb = boto3.resource("dynamodb")
sqs = boto3.client("sqs")


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    try:
        user_id = (
            event.get("requestContext", {})
            .get("authorizer", {})
            .get("claims", {})
            .get("sub")
        )
    except (AttributeError, TypeError):
        user_id = None

    if not user_id:
        return response(401, {"error": "Unauthorized"})

    try:
        body = json.loads(event.get("body") or "{}")
        video_id = body.get("video_id")
    except (json.JSONDecodeError, AttributeError):
        video_id = None

    if not video_id:
        return response(400, {"error": "Missing video_id"})

    summarization_jobs_table_name = os.environ.get(
        "SUMMARIZATION_JOBS_TABLE", "summarization-jobs"
    )
    youtube_summaries_table_name = os.environ.get(
        "YOUTUBE_SUMMARIES_TABLE", "youtube-summaries"
    )
    sqs_queue_url = os.environ.get("SQS_QUEUE_URL")

    summaries_table = dynamodb.Table(youtube_summaries_table_name)
    cached = summaries_table.get_item(Key={"video_id": video_id})
    if "Item" in cached:
        return response(
            200,
            {"status": "COMPLETED", "cached": True, "data": cached["Item"]},
        )

    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    jobs_table = dynamodb.Table(summarization_jobs_table_name)
    jobs_table.put_item(
        Item={
            "job_id": job_id,
            "video_id": video_id,
            "user_id": user_id,
            "status": "PENDING",
            "created_at": now,
            "updated_at": now,
        }
    )

    sqs.send_message(
        QueueUrl=sqs_queue_url,
        MessageBody=json.dumps(
            {"job_id": job_id, "video_id": video_id, "user_id": user_id}
        ),
    )

    return response(202, {"job_id": job_id, "status": "PENDING"})
