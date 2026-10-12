import os
import logging
import json
import re
import time
import random
from datetime import datetime, timezone
import boto3
import urllib.request
import urllib.error
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
            return None, None, "This video is unavailable (deleted, private, or region-blocked).", 400
        except TranscriptsDisabled:
            return None, None, "Transcripts are disabled for this video.", 400
        except NoTranscriptFound:
            return None, None, "No transcript found for this video in any language.", 400
        except Exception as e:
            last_error = str(e)
            logger.warning(f"Transcript fetch failed with proxy '{proxy_url}': {last_error}")

    return None, None, f"All proxies exhausted. Last error: {last_error}", 429

def get_video_title(video_id: str) -> str:
    """Fetches the video title via YouTube's public oEmbed API."""
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get("title", "Unknown Title")
    except Exception as e:
        logger.warning(f"Failed to fetch video titel for {video_id}: {str(e)}")
        return "Unknown Title"

def check_cache(video_id):
    """Checks if the summary already exists in DynamoDB."""
    try:
        table = dynamodb.Table(config.YOUTUBE_SUMMARIES_TABLE)
        response = table.get_item(Key={'video_id': video_id})
        if 'Item' in response:
            return response['Item']
    except ClientError as e:
        logger.error(f"DynamoDB read error (youtube-summaries): {e.response['Error']['Message']}")
    return None

def save_to_cache(video_id, title, summary):
    """Saves the generated summary to DynamoDB."""
    try:
        table = dynamodb.Table(config.YOUTUBE_SUMMARIES_TABLE)
        table.put_item(
            Item={
                'video_id': video_id,
                'title': title,
                'summary': summary
            }
        )
    except ClientError as e:
        logger.error(f"DynamoDB write error (youtube-summaries): {e.response['Error']['Message']}")

def upload_transcript_to_s3(video_id, title, raw_transcript):
    """Uploads the raw transcript payload to S3 without blocking the main execution."""
    if not getattr(config, 'TRANSCRIPT_BUCKET', None):
        logger.warning("TRANSCRIPT_BUCKET not configured. Skipping S3 upload.")
        return

    try:
        payload = {
            "video_id": video_id,
            "title": title,
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

def update_job_status(job_id, status, result_payload=None, error_message=None):
    """Updates the job status in SUMMARIZATION_JOBS_TABLE."""
    try:
        table = dynamodb.Table(config.SUMMARIZATION_JOBS_TABLE)
        update_expr = "SET #s = :s, updated_at = :u"
        expr_names = {"#s": "status"}
        expr_values = {
            ":s": status,
            ":u": datetime.now(timezone.utc).isoformat(),
        }
        if result_payload is not None:
            update_expr += ", #res = :r"
            expr_names["#res"] = "result"
            expr_values[":r"] = result_payload
        if error_message is not None:
            update_expr += ", error_message = :e"
            expr_values[":e"] = error_message
        table.update_item(
            Key={"job_id": job_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )
    except ClientError as e:
        logger.error(f"Failed to update job status for job_id={job_id}: {e.response['Error']['Message']}")


def _process_record(record):
    """Processes a single SQS record."""
    body = json.loads(record["body"])
    job_id = body["job_id"]
    video_id = body["video_id"]
    user_id = body["user_id"]

    logger.info(f"Processing job_id={job_id}, video_id={video_id}, user_id={user_id}")
    update_job_status(job_id, "PROCESSING")

    transcript, raw_transcript, error, _ = get_transcript(video_id)
    if error:
        raise RuntimeError(f"Transcript fetch failed: {error}")

    logger.info(f"Transcript fetched. Length: {len(transcript)} characters.")

    video_title = get_video_title(video_id)
    logger.info(f"Video Title: {video_title}")

    upload_transcript_to_s3(video_id, video_title, raw_transcript)

    logger.info("Sending transcript to OpenAI...")
    summary, llm_error, _ = summarise(transcript)
    if llm_error:
        raise RuntimeError(f"LLM summarization failed: {llm_error}")

    logger.info("Summary generated. Saving to DynamoDB.")
    save_to_cache(video_id, video_title, summary)
    record_user_submission(user_id, video_id)

    result = {"video_id": video_id, "title": video_title, "summary": summary}
    update_job_status(job_id, "COMPLETED", result_payload=result)
    logger.info(f"Job {job_id} completed successfully.")


def lambda_handler(event, context):
    for record in event.get("Records", []):
        body = json.loads(record.get("body", "{}"))
        job_id = body.get("job_id", "unknown")
        try:
            _process_record(record)
        except Exception as e:
            logger.exception(f"Failed to process job_id={job_id}: {str(e)}")
            update_job_status(job_id, "FAILED", error_message=str(e))
            raise
