import os
import json
import re
import boto3
from botocore.exceptions import ClientError
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, VideoUnavailable, NoTranscriptFound
from openai import OpenAI

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
ssm = boto3.client('ssm')

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "youtube-summaries")
SSM_PARAM_NAME = os.environ.get("SSM_PARAM_NAME", "/youtube-summarizer/openai-api-key")

# Global variable to cache the OpenAI client between warm Lambda invocations
openai_client = None

def get_openai_client():
    """Fetches the OpenAI API key securely from SSM Parameter Store (Lazy Load)."""
    global openai_client
    if not openai_client:
        try:
            response = ssm.get_parameter(
                Name=SSM_PARAM_NAME,
                WithDecryption=True
            )
            api_key = response['Parameter']['Value']
            openai_client = OpenAI(api_key=api_key)
        except Exception as e:
            print(f"Error fetching API key from SSM: {str(e)}")
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

def format_prompt_v2(content):
    return f"""
            I'm sharing a transcript for my personal learning.
            Please extract and summarize all the key insights and takeaways to help me quickly understand the most important information.
            Present the output as clear bullet points, grouped logically by theme or topic. This is the transcript:
            {content}
            """

def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        full_content = " ".join(snippet['text'] for snippet in transcript_list)
        return full_content, None
    except (TranscriptsDisabled, VideoUnavailable, NoTranscriptFound) as e:
        return None, str(e)
    except Exception as e:
        return None, f"An error occurred: {str(e)}"

def check_cache(video_id):
    """Checks if the summary already exists in DynamoDB."""
    try:
        table = dynamodb.Table(TABLE_NAME)
        response = table.get_item(Key={'video_id': video_id})
        if 'Item' in response:
            return response['Item'].get('summary')
    except ClientError as e:
        print(f"DynamoDB read error: {e.response['Error']['Message']}")
    return None

def save_to_cache(video_id, summary):
    """Saves the generated summary to DynamoDB."""
    try:
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(
            Item={
                'video_id': video_id,
                'summary': summary
            }
        )
    except ClientError as e:
        print(f"DynamoDB write error: {e.response['Error']['Message']}")

def summarise(content):
    client = get_openai_client()
    if not client:
        return None, "OpenAI client is not initialized. Check SSM configuration."

    engine = "gpt-4o-mini"
    max_tokens = 1000
    temperature = 0.7

    prompt = format_prompt_v2(content)

    try:
        completion = client.chat.completions.create(
            model=engine,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            n=1
        )
        return completion.choices[0].message.content, None
    except Exception as e:
        return None, f"LLM Provider Error: {str(e)}"

# AWS Lambda Entry Point
def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        youtube_url = body.get('url')

        # 1. Validate URL
        video_id = extract_and_validate_video_id(youtube_url)
        if not video_id:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Invalid or missing YouTube URL.'})
            }

        # 2. Check Database Cache
        cached_summary = check_cache(video_id)
        if cached_summary:
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'summary': cached_summary, 'source': 'cache'})
            }

        # 3. Fetch Transcript
        transcript, error = get_transcript(video_id)
        if error:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': error})
            }

        # 4. Summarize via LLM
        summary, llm_error = summarise(transcript)
        if llm_error:
            return {
                'statusCode': 502,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': llm_error})
            }

        # 5. Save to Cache
        save_to_cache(video_id, summary)

        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'summary': summary, 'source': 'llm'})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }