import os
import json
import logging
from decimal import Decimal

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')

SUMMARIZATION_JOBS_TABLE = os.environ.get('SUMMARIZATION_JOBS_TABLE', 'summarization-jobs')

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': '*',
    'Access-Control-Allow-Methods': 'OPTIONS,GET',
}


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)


def response(status_code: int, body: dict) -> dict:
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps(body, cls=DecimalEncoder),
    }


def extract_user_id(event: dict) -> str | None:
    try:
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
        return claims.get('sub') or None
    except Exception as e:
        logger.error(f"Failed to extract user_id: {str(e)}")
        return None


def get_job(job_id: str) -> dict | None:
    table = dynamodb.Table(SUMMARIZATION_JOBS_TABLE)
    try:
        result = table.get_item(Key={'job_id': job_id})
        return result.get('Item')
    except ClientError as e:
        logger.error(f"DynamoDB get_item error (summarization-jobs): {e.response['Error']['Message']}")
        return None


def lambda_handler(event: dict, context) -> dict:
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': CORS_HEADERS, 'body': ''}

    user_id = extract_user_id(event)
    if not user_id:
        logger.warning("Unauthorized: missing sub claim.")
        return response(401, {'error': 'Unauthorized'})

    job_id = (event.get('pathParameters') or {}).get('job_id')
    if not job_id:
        logger.warning("Bad request: missing job_id path parameter.")
        return response(400, {'error': 'Missing job_id'})

    logger.info(f"Fetching job status for job_id={job_id}, user_id={user_id}")

    job = get_job(job_id)
    if job is None:
        return response(404, {'error': 'Not Found'})

    if job.get('user_id') != user_id:
        logger.warning(f"Forbidden: job_id={job_id} does not belong to user_id={user_id}")
        return response(403, {'error': 'Forbidden'})

    return response(200, job)
