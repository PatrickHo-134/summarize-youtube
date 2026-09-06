# Project Context: YouTube Summarizer (AWS Cloud-Native)

## 1. Project Overview & Architecture
- **Goal:** Serverless full-stack web application that accepts a YouTube URL, fetches the transcript, generates a summary via OpenAI, and caches results in DynamoDB.
- **Frontend:** Static web UI (`index.html`, `app.js`) hosted in a private S3 bucket and served globally via AWS CloudFront.
- **API Layer:** AWS API Gateway (REST API) routing requests to AWS Lambda.
- **Backend:** AWS Lambda function in Python 3.13 (`x86_64` architecture / Amazon Linux).
- **Storage & Config:** DynamoDB (cache), AWS SSM Parameter Store (OpenAI API key), Lambda Environment Variables (`PROXY_URL`).

---

## 2. Infrastructure & Endpoint Configuration
- **CloudFront Domain:** `https://d1lixi6ffoheyhp.cloudfront.net`
  - Access Control: Origin Access Control (OAC) targeting private S3 bucket.
  - Default Root Object: `index.html`
- **API Gateway ID:** `etx5b18bqf`
  - Resource Path: `/summarize`
  - HTTP Method: `POST` (with `OPTIONS` enabled for CORS preflight).
  - Stage: `prod`
  - Full Endpoint URL: `https://etx5b18bqf.execute-api.ap-southeast-2.amazonaws.com/prod/summarize`
- **Lambda Function:** `youtube-summarizer`
  - Runtime: **Python 3.13** (Architecture: `x86_64`)
  - Timeout: 30 seconds.
  - IAM Roles: `AmazonDynamoDBFullAccess`, `AmazonSSMReadOnlyAccess`.

---

## 3. Key Issues Resolved & Solutions

### A. Endpoint Path & CORS (502 / Preflight Failures)
- **Problem:** `app.js` called `/prod` instead of `/prod/summarize`, causing CORS headers to be missed.
- **Fix:** Set `API_ENDPOINT` to `https://etx5b18bqf.execute-api.ap-southeast-2.amazonaws.com/prod/summarize` and redeployed API Gateway stage `prod`.

### B. Binaries Mismatch (`pydantic_core`)
- **Problem:** Local build on macOS caused `ImportModuleError: No module named 'pydantic_core._pydantic_core'` on Lambda's Linux environment.
- **Fix:** Built packaging using cross-platform Linux flags for Python 3.13:
  ```bash
  rm -rf package deployment.zip && mkdir package
  pip install\
    --platform manylinux2014_x86_64\
    --target=./package\
    --implementation cp\
    --python-version 3.13\
    --only-binary=:all: --upgrade\
    youtube-transcript-api openai
  cp src/lambda_function.py package/
  cd package && zip -r ../deployment.zip . && cd ..
     ```

### C. `youtube-transcript-api` Breaking Change (v1.0.0+)

-   **Problem:** Static method `YouTubeTranscriptApi.get_transcript()` was removed in version 1.0.0+.

-   **Fix:** Refactored code to instantiate the class (`ytt_api = YouTubeTranscriptApi()`) and call `ytt_api.fetch(video_id)` followed by `.to_raw_data()`.

### D. AWS Datacenter IP Block by YouTube

-   **Problem:** YouTube blocked transcript requests originating from AWS cloud provider IP ranges.

-   **Fix:** Integrated residential proxies (via DataImpulse gateway configured at `http://USERNAME:PASSWORD@gw.dataimpulse.com:823`) injected through the `PROXY_URL` environment variable and handled via `GenericProxyConfig`.

### E. Runtime ImportModuleError (`youtube_transcript_api` missing)

-   **Problem:** Zipping the parent `package/` folder instead of its contents caused Lambda to fail finding modules at runtime.

-   **Fix:** Created an automated build script (`build.sh`) to consistently handle cleaning, cross-platform installation, and correct root-level zipping.

4\. Current Code Base (`src/lambda_function.py`)
------------------------------------------------


```Python
import os
import logging
import json
import re
import boto3
from botocore.exceptions import ClientError
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, VideoUnavailable, NoTranscriptFound
from youtube_transcript_api.proxies import GenericProxyConfig
from openai import OpenAI

# Initialize the logger at the global level
logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
        # Check for the Proxy URL environment variable
        proxy_url = os.environ.get("PROXY_URL")

        # Instantiate the API object, using the proxy if the variable exists
        if proxy_url:
            proxy_config = GenericProxyConfig(
                http_url=proxy_url,
                https_url=proxy_url
            )
            ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
        else:
            ytt_api = YouTubeTranscriptApi()

        # Fetch the transcript object
        fetched_transcript = ytt_api.fetch(video_id)

        # Convert back to the list of dictionaries
        transcript_list = fetched_transcript.to_raw_data()

        # Combine text segments into a single string
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
        logger.info(f"Incoming event body: {event.get('body')}")

        body = json.loads(event.get('body', '{}'))
        youtube_url = body.get('url')

        # Validate URL
        video_id = extract_and_validate_video_id(youtube_url)
        if not video_id:
            logger.warning(f"URL validation failed for input: {youtube_url}")
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Invalid or missing YouTube URL.'})
            }

        logger.info(f"Successfully extracted Video ID: {video_id}")

        # Log the cache check
        logger.info("Checking DynamoDB cache...")
        cached_summary = check_cache(video_id)
        if cached_summary:
            logger.info("Cache hit. Returning cached summary.")
            return {
                'statusCode': 200,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'summary': cached_summary, 'source': 'cache'})
            }

        # Log the transcript fetch (Common failure point)
        proxy_configured = bool(os.environ.get('PROXY_URL'))
        logger.info(f"Cache miss. Fetching transcript... (Proxy Configured: {proxy_configured})")

        transcript, error = get_transcript(video_id)
        if error:
            logger.error(f"Transcript fetch failed: {error}")
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': error})
            }

        logger.info(f"Transcript fetched successfully. Length: {len(transcript)} characters.")

        # Log the LLM execution (Another common timeout point)
        logger.info("Sending transcript to OpenAI...")
        summary, llm_error = summarise(transcript)
        if llm_error:
            logger.error(f"OpenAI API failed: {llm_error}")
            return {
                'statusCode': 502,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': llm_error})
            }

        logger.info("Successfully generated summary. Saving to cache.")
        save_to_cache(video_id, summary)

        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'summary': summary, 'source': 'llm'})
        }

    except Exception as e:
        # Log unexpected crashes with full stack traces
        logger.exception("An unexpected error occurred during Lambda execution.")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': "Internal server error."})
        }

```

5\. Automation (`build.sh`)
---------------------------

-   Automated build script to handle packaging and zipping cleanly:
    ```Bash
    #!/bin/bash
    set -e
    rm -rf package deployment.zip
    mkdir -p package
    pip install\
      --platform manylinux2014_x86_64\
      --target=./package\
      --implementation cp\
      --python-version 3.13\
      --only-binary=:all: --upgrade\
      youtube-transcript-api openai
    cp src/lambda_function.py package/
    cd package && zip -r ../deployment.zip . && cd ..

    ```

- Make the script executable once in your terminal:
     ```bash
     chmod +x build.sh
     ```

- Run it whenever you update your code or need to rebuild:
     ```
     ./build.sh
     ```
