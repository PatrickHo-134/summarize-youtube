import os
import logging
import json
import re
import time
import random
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, VideoUnavailable, NoTranscriptFound
from youtube_transcript_api.proxies import GenericProxyConfig
from openai import OpenAI
from openai import RateLimitError, APITimeoutError, BadRequestError
from src import config

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
ssm = boto3.client('ssm')
s3 = boto3.client('s3')

# Cache OpenAI client across warm Lambda invocations
openai_client = None

def get_openai_client():
    """Fetches the OpenAI API key securely from SSM Parameter Store (Lazy Load)."""
    global openai_client
    if not openai_client:
        try:
            response = ssm.get_parameter(
                Name=config.SSM_PARAM_NAME,
                WithDecryption=True
            )
            api_key = response['Parameter']['Value']
            openai_client = OpenAI(api_key=api_key)
        except Exception as e:
            logger.error(f"Error fetching API key from SSM: {str(e)}")
    return openai_client

def extract_and_validate_video_id(youtube_url):
    """
    Validates the YouTube URL using RegEx and extracts the 11-character video ID.
    """
    if not youtube_url or not isinstance(youtube_url, str):
        return None

    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
    match = re.search(pattern, youtube_url.strip())

    if match:
        return match.group(1)
    return None

def extract_user_id(event):
    """Extracts unique user ID (sub claim) injected by API Gateway Cognito Authorizer."""
    try:
        claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
        return claims.get('sub')
    except Exception as e:
        logger.error(f"Failed to extract user_id from context: {str(e)}")
        return None

def format_prompt_v2(content):
    return f"""
            I'm sharing a transcript for my personal learning.
            Please extract and summarize all the key insights and takeaways to help me quickly understand the most important information.
            Present the output as clear bullet points, grouped logically by theme or topic. This is the transcript:
            {content}
            """

def _get_proxy_pool():
    pool_env = config.PROXY_POOL_URLS
    if not pool_env:
        return [None]
    proxies = [p.strip() for p in pool_env.split(",") if p.strip()]
    return proxies if proxies else [None]


def get_transcript(video_id):
    proxies = _get_proxy_pool()
    last_error = None

    for attempt, proxy_url in enumerate(proxies):
        if attempt > 0:
            backoff = (2 ** attempt) + random.uniform(0, 1)
            logger.warning(f"Proxy attempt {attempt} failed. Retrying with next proxy in {backoff:.2f}s.")
            time.sleep(backoff)

        try:
            if proxy_url:
                proxy_config = GenericProxyConfig(
                    http_url=proxy_url,
                    https_url=proxy_url
                )
                ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
            else:
                ytt_api = YouTubeTranscriptApi()

            fetched_transcript = ytt_api.fetch(video_id)
            transcript_list = fetched_transcript.to_raw_data()
            full_content = " ".join(snippet['text'] for snippet in transcript_list)
            return full_content, transcript_list, None, None

        except VideoUnavailable:
            return None, "This video is unavailable (deleted, private, or region-blocked).", 400
        except TranscriptsDisabled:
            return None, "Transcripts are disabled for this video.", 400
        except NoTranscriptFound:
            return None, "No transcript found for this video in any language.", 400
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Transcript fetch failed with proxy '{proxy_url}': {last_error}")

    return None, None, f"All proxies exhausted. Last error: {last_error}", 429

def check_cache(video_id):
    """Checks if the summary already exists in DynamoDB."""
    try:
        table = dynamodb.Table(config.YOUTUBE_SUMMARIES_TABLE)
        response = table.get_item(Key={'video_id': video_id})
        if 'Item' in response:
            return response['Item'].get('summary')
    except ClientError as e:
        logger.error(f"DynamoDB read error (youtube-summaries): {e.response['Error']['Message']}")
    return None

def save_to_cache(video_id, summary):
    """Saves the generated summary to DynamoDB."""
    try:
        table = dynamodb.Table(config.YOUTUBE_SUMMARIES_TABLE)
        table.put_item(
            Item={
                'video_id': video_id,
                'summary': summary
            }
        )
    except ClientError as e:
        logger.error(f"DynamoDB write error (youtube-summaries): {e.response['Error']['Message']}")

def upload_transcript_to_s3(video_id, raw_transcript):
    """Uploads the raw transcript payload to S3 without blocking the main execution."""
    if not getattr(config, 'TRANSCRIPT_BUCKET', None):
        logger.warning("TRANSCRIPT_BUCKET not configured. Skipping S3 upload.")
        return

    try:
        payload = {
            "video_id": video_id,
            "fetched_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "language": "en",
            "transcript": raw_transcript
        }

        s3_key = f"transcripts/{video_id}.json"

        s3.put_object(
            Bucket=config.TRANSCRIPT_BUCKET,
            Key=s3_key,
            Body=json.dumps(payload),
            ContentType="application/json"
        )
        logger.info(f"Successfully uploaded raw transcript to s3://{config.TRANSCRIPT_BUCKET}/{s3_key}")
    except Exception as e:
        logger.error(f"S3 Upload failed for {video_id}: {str(e)}. Proceeding to LLM summarization")

def record_user_submission(user_id, video_id):
    """Records mapping between user_id and video_id in user-submissions table."""
    try:
        table = dynamodb.Table(config.USER_SUBMISSIONS_TABLE)
        table.put_item(
            Item={
                'user_id': user_id,
                'video_id': video_id,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        )
        logger.info(f"Recorded user submission: user_id={user_id}, video_id={video_id}")
    except ClientError as e:
        logger.error(f"DynamoDB write error (user-submissions): {e.response['Error']['Message']}")

def summarise(content):
    client = get_openai_client()
    if not client:
        return None, "OpenAI client is not initialized. Check SSM configuration.", 502

    prompt = format_prompt_v2(content)

    try:
        completion = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS,
            n=1
        )
        return completion.choices[0].message.content, None, None
    except RateLimitError:
        return None, "OpenAI rate limit reached. Please try again in a moment.", 429
    except APITimeoutError:
        return None, "OpenAI request timed out. Please try again.", 504
    except BadRequestError as e:
        if "context_length_exceeded" in str(e) or "maximum context length" in str(e).lower():
            return None, "This video's transcript is too long to summarize.", 400
        return None, f"OpenAI rejected the request: {str(e)}", 400
    except Exception as e:
        return None, f"LLM Provider Error: {str(e)}", 502

def lambda_handler(event, context):
    try:
        logger.info(f"Incoming event body: {event.get('body')}")

        # Extract & validate authenticated user identity
        user_id = extract_user_id(event)
        if not user_id:
            logger.warning("Unauthorized access attempt: Missing or invalid user claims.")
            return {
                'statusCode': 401,
                'headers': {'Access-Control-Allow-Origin': config.CORS_ALLOW_ORIGIN},
                'body': json.dumps({'error': 'Unauthorized user token.'})
            }

        logger.info(f"Request authorized for User ID: {user_id}")

        body = json.loads(event.get('body', '{}'))
        youtube_url = body.get('url')

        # Validate URL
        video_id = extract_and_validate_video_id(youtube_url)
        if not video_id:
            logger.warning(f"URL validation failed for input: {youtube_url}")
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': config.CORS_ALLOW_ORIGIN},
                'body': json.dumps({'error': 'Invalid or missing YouTube URL.'})
            }

        logger.info(f"Successfully extracted Video ID: {video_id}")

        # Record ownership mapping for this user
        record_user_submission(user_id, video_id)

        # Log the cache check
        logger.info("Checking DynamoDB cache...")
        cached_summary = check_cache(video_id)
        if cached_summary:
            logger.info("Cache hit. Returning cached summary.")
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': config.CORS_ALLOW_ORIGIN},
                'body': json.dumps({'summary': cached_summary, 'source': 'cache'})
            }

        # Log the transcript fetch (Common failure point)
        proxy_configured = bool(os.environ.get('PROXY_URL'))
        logger.info(f"Cache miss. Fetching transcript... (Proxy Configured: {proxy_configured})")

        transcript, raw_transcript, error, error_status = get_transcript(video_id)
        if error:
            logger.error(f"Transcript fetch failed: {error}")
            return {
                'statusCode': error_status,
                'headers': {'Access-Control-Allow-Origin': config.CORS_ALLOW_ORIGIN},
                'body': json.dumps({'error': error})
            }

        logger.info(f"Transcript fetched successfully. Length: {len(transcript)} characters.")

        upload_transcript_to_s3(video_id, raw_transcript)

        # Log the LLM execution (Another common timeout point)
        logger.info("Sending transcript to OpenAI...")
        summary, llm_error, llm_status = summarise(transcript)
        if llm_error:
            logger.error(f"OpenAI API failed: {llm_error}")
            return {
                'statusCode': llm_status,
                'headers': {'Access-Control-Allow-Origin': config.CORS_ALLOW_ORIGIN},
                'body': json.dumps({'error': llm_error})
            }

        logger.info("Successfully generated summary. Saving to cache.")
        save_to_cache(video_id, summary)

        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': config.CORS_ALLOW_ORIGIN},
            'body': json.dumps({'summary': summary, 'source': 'llm'})
        }

    except Exception as e:
        logger.exception("An unexpected error occurred during Lambda execution.")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': config.CORS_ALLOW_ORIGIN},
            'body': json.dumps({'error': "Internal server error."})
        }