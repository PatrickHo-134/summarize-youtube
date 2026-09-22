import os
import logging
import json
import base64
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')

USER_SUBMISSIONS_TABLE = os.environ.get('USER_SUBMISSIONS_TABLE', 'user-submissions')
YOUTUBE_SUMMARIES_TABLE = os.environ.get('YOUTUBE_SUMMARIES_TABLE', 'youtube-summaries')
CORS_ALLOW_ORIGIN = os.environ.get('CORS_ALLOW_ORIGIN', '*')

CORS_HEADERS = {
    'Access-Control-Allow-Origin': CORS_ALLOW_ORIGIN,
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'Access-Control-Allow-Methods': 'GET,OPTIONS',
}


def _response(status_code: int, body: dict) -> dict:
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps(body),
    }


def extract_user_id(event: dict) -> str | None:
    try:
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
        return claims.get('sub') or None
    except Exception as e:
        logger.error(f"Failed to extract user_id: {str(e)}")
        return None


def _decode_next_token(token: str) -> dict | None:
    try:
        return json.loads(base64.b64decode(token).decode('utf-8'))
    except Exception as e:
        logger.warning(f"Failed to decode next_token: {e}")
        return None


def _encode_next_token(key: dict) -> str:
    return base64.b64encode(json.dumps(key).encode('utf-8')).decode('utf-8')


def get_submissions(user_id: str, limit: int, exclusive_start_key: dict | None) -> tuple[list[dict], dict | None]:
    """Query user-submissions table for a page of records belonging to user_id."""
    table = dynamodb.Table(USER_SUBMISSIONS_TABLE)
    try:
        kwargs = {
            'KeyConditionExpression': boto3.dynamodb.conditions.Key('user_id').eq(user_id),
            'Limit': limit,
        }
        if exclusive_start_key:
            kwargs['ExclusiveStartKey'] = exclusive_start_key
        response = table.query(**kwargs)
        return response.get('Items', []), response.get('LastEvaluatedKey')
    except ClientError as e:
        logger.error(f"DynamoDB query error (user-submissions): {e.response['Error']['Message']}")
        return [], None


def batch_get_summaries(video_ids: list[str]) -> dict[str, dict]:
    """
    Fetch video_id, title, and summary from youtube-summaries for a list of video IDs.
    Returns a dict keyed by video_id.
    """
    if not video_ids:
        return {}

    client = boto3.client('dynamodb')
    keys = [{'video_id': {'S': vid}} for vid in video_ids]

    try:
        response = client.batch_get_item(
            RequestItems={
                YOUTUBE_SUMMARIES_TABLE: {
                    'Keys': keys,
                    'ProjectionExpression': 'video_id, title, summary',
                }
            }
        )
        items = response.get('Responses', {}).get(YOUTUBE_SUMMARIES_TABLE, [])
        result = {}
        for item in items:
            vid = item['video_id']['S']
            result[vid] = {
                'title': item.get('title', {}).get('S', ''),
                'summary': item.get('summary', {}).get('S', ''),
            }
        return result
    except ClientError as e:
        logger.error(f"DynamoDB batch_get_item error (youtube-summaries): {e.response['Error']['Message']}")
        return {}


def build_video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def lambda_handler(event: dict, context) -> dict:
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    user_id = extract_user_id(event)
    if not user_id:
        logger.warning("Unauthorized: missing sub claim.")
        return _response(401, {'error': 'Unauthorized.'})

    logger.info(f"Fetching history for user_id={user_id}")

    query_params = event.get('queryStringParameters') or {}
    try:
        limit = min(int(query_params.get('limit', 10)), 50)
    except (ValueError, TypeError):
        limit = 10
    raw_token = query_params.get('next_token')
    exclusive_start_key = _decode_next_token(raw_token) if raw_token else None

    submissions, last_evaluated_key = get_submissions(user_id, limit, exclusive_start_key)
    if not submissions:
        return _response(200, {'items': [], 'next_token': None})

    video_ids = [s['video_id'] for s in submissions]
    summaries_map = batch_get_summaries(video_ids)

    created_at_map = {s['video_id']: s.get('created_at', '') for s in submissions}

    items = []
    for video_id in video_ids:
        summary_data = summaries_map.get(video_id, {})
        items.append({
            'videoId': video_id,
            'videoUrl': build_video_url(video_id),
            'title': summary_data.get('title', ''),
            'summary': summary_data.get('summary', ''),
            'createdAt': created_at_map.get(video_id, ''),
        })

    items.sort(key=lambda x: x['createdAt'], reverse=True)

    next_token = _encode_next_token(last_evaluated_key) if last_evaluated_key else None

    return _response(200, {'items': items, 'next_token': next_token})
