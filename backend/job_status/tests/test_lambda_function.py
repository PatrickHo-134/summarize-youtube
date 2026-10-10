import os
import json
import boto3
import pytest
from moto import mock_aws

os.environ['AWS_DEFAULT_REGION'] = 'ap-southeast-2'
os.environ['SUMMARIZATION_JOBS_TABLE'] = 'summarization-jobs'

from src.lambda_function import lambda_handler

TABLE_NAME = 'summarization-jobs'

OPTIONS_EVENT = {
    'httpMethod': 'OPTIONS',
    'requestContext': {},
}


def make_event(job_id=None, claims=None, include_path_params=True):
    event = {
        'httpMethod': 'GET',
        'requestContext': {
            'authorizer': {
                'claims': claims if claims is not None else {'sub': 'test-user-abc'}
            }
        },
    }
    if include_path_params:
        event['pathParameters'] = {'job_id': job_id} if job_id is not None else {}
    return event


@pytest.fixture
def jobs_table():
    with mock_aws():
        client = boto3.client('dynamodb', region_name='ap-southeast-2')
        client.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{'AttributeName': 'job_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'job_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST',
        )
        yield boto3.resource('dynamodb', region_name='ap-southeast-2').Table(TABLE_NAME)


# ---------------------------------------------------------------------------
# CORS preflight
# ---------------------------------------------------------------------------

def test_options_preflight_returns_200():
    response = lambda_handler(OPTIONS_EVENT, {})
    assert response['statusCode'] == 200
    assert response['headers']['Access-Control-Allow-Origin'] == '*'
    assert response['headers']['Access-Control-Allow-Headers'] == '*'
    assert response['headers']['Access-Control-Allow-Methods'] == 'OPTIONS,GET'


# ---------------------------------------------------------------------------
# 401 Unauthorized
# ---------------------------------------------------------------------------

def test_missing_sub_returns_401(jobs_table):
    event = make_event(job_id='job-1', claims={})
    response = lambda_handler(event, {})

    assert response['statusCode'] == 401
    body = json.loads(response['body'])
    assert body['error'] == 'Unauthorized'


# ---------------------------------------------------------------------------
# 400 Missing job_id
# ---------------------------------------------------------------------------

def test_missing_job_id_returns_400(jobs_table):
    event = make_event(job_id=None)
    response = lambda_handler(event, {})

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error'] == 'Missing job_id'


def test_missing_path_parameters_returns_400(jobs_table):
    event = make_event(include_path_params=False)
    response = lambda_handler(event, {})

    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert body['error'] == 'Missing job_id'


# ---------------------------------------------------------------------------
# 404 Not Found
# ---------------------------------------------------------------------------

def test_job_not_found_returns_404(jobs_table):
    event = make_event(job_id='nonexistent-job')
    response = lambda_handler(event, {})

    assert response['statusCode'] == 404
    body = json.loads(response['body'])
    assert body['error'] == 'Not Found'


# ---------------------------------------------------------------------------
# 403 Forbidden (wrong user)
# ---------------------------------------------------------------------------

def test_job_belongs_to_other_user_returns_403(jobs_table):
    jobs_table.put_item(Item={
        'job_id': 'job-1',
        'user_id': 'someone-else',
        'video_id': 'vid123',
        'status': 'PENDING',
    })

    event = make_event(job_id='job-1', claims={'sub': 'test-user-abc'})
    response = lambda_handler(event, {})

    assert response['statusCode'] == 403
    body = json.loads(response['body'])
    assert body['error'] == 'Forbidden'


# ---------------------------------------------------------------------------
# 200 Success
# ---------------------------------------------------------------------------

def test_pending_job_returns_200(jobs_table):
    jobs_table.put_item(Item={
        'job_id': 'job-1',
        'user_id': 'test-user-abc',
        'video_id': 'vid123',
        'status': 'PENDING',
        'created_at': '2026-10-01T00:00:00Z',
    })

    event = make_event(job_id='job-1')
    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    assert response['headers']['Access-Control-Allow-Origin'] == '*'
    body = json.loads(response['body'])
    assert body['job_id'] == 'job-1'
    assert body['status'] == 'PENDING'
    assert body['video_id'] == 'vid123'


def test_completed_job_returns_result_payload(jobs_table):
    jobs_table.put_item(Item={
        'job_id': 'job-2',
        'user_id': 'test-user-abc',
        'video_id': 'vid456',
        'status': 'COMPLETED',
        'result': {'title': 'Test Video', 'summary': '- point one\n- point two'},
    })

    event = make_event(job_id='job-2')
    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['status'] == 'COMPLETED'
    assert body['result']['title'] == 'Test Video'
    assert body['result']['summary'] == '- point one\n- point two'


def test_failed_job_returns_error_message(jobs_table):
    jobs_table.put_item(Item={
        'job_id': 'job-3',
        'user_id': 'test-user-abc',
        'video_id': 'vid789',
        'status': 'FAILED',
        'error_message': 'Transcript unavailable for this video.',
    })

    event = make_event(job_id='job-3')
    response = lambda_handler(event, {})

    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert body['status'] == 'FAILED'
    assert body['error_message'] == 'Transcript unavailable for this video.'
