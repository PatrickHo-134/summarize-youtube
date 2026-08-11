Here is a review of your script, a simple UI to interact with it, and a comprehensive plan to deploy this architecture on AWS.

1\. Code Improvements
---------------------

Your script is on the right track, but there are a few bugs, security risks, and architectural tweaks to address before moving it to the cloud.

### Key Issues to Fix

-   **Variable Scope Bug:** In your `summarise(content)` function, you are calling `format_prompt_v2(transcript)`. `transcript` is a global variable from the execution block. It should be passing the `content` argument instead.

-   **Transcript API Usage:** `YouTubeTranscriptApi` is typically called directly via its class method `YouTubeTranscriptApi.get_transcript(video_id)`. Furthermore, it returns a list of dictionaries, meaning you must access the text using `snippet['text']` rather than `snippet.text`.

-   **Hardcoded Secrets:** Hardcoding `api_key` and `openai_org_id` is a security risk, especially when deploying to AWS. These should be pulled from environment variables.

-   **Unused Code:** You can remove the unused `WebshareProxyConfig` import and the old `format_prompt` function.

-   **Model Flexibility:** While `gpt-4o-mini` is great, you could easily modularize the `summarise` function to swap OpenAI for Anthropic's Claude platform if you want to experiment with different LLM reasoning styles.

### Refactored Code (Prepared for AWS Lambda)

To run this in AWS Lambda, the script needs an entry point called a `lambda_handler`. Here is the refactored, cloud-ready version:

Python

```
import os
import json
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, VideoUnavailable, NoTranscriptFound
from openai import OpenAI

# Initialize the OpenAI client using environment variables
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
    organization=os.environ.get("OPENAI_ORG_ID"),
    project=os.environ.get("OPENAI_PROJECT_ID")
)

def format_prompt_v2(content):
    return f"""
            I'm sharing a transcript for my personal learning.
            Please extract and summarize all the key insights and takeaways to help me quickly understand the most important information.
            Present the output as clear bullet points, grouped logically by theme or topic. This is the transcript:
            {content}
            """

def get_transcript(youtube_url):
    try:
        video_id = youtube_url.split("v=")[-1].split("&")[0]

        # Standard method for fetching transcripts
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

        # Access dictionary keys properly
        full_content = " ".join(snippet['text'] for snippet in transcript_list)
        return full_content, None

    except (TranscriptsDisabled, VideoUnavailable, NoTranscriptFound) as e:
        return None, str(e)
    except Exception as e:
        return None, f"An error occurred: {str(e)}"

def summarise(content):
    engine = "gpt-4o-mini"
    max_tokens = 1000
    temperature = 0.7

    prompt = format_prompt_v2(content) # Fixed variable scope

    completion = client.chat.completions.create(
        model=engine,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
        n=1
    )
    return completion.choices[0].message.content

# AWS Lambda Entry Point
def lambda_handler(event, context):
    try:
        # Parse the URL from the API Gateway request body
        body = json.loads(event.get('body', '{}'))
        youtube_url = body.get('url')

        if not youtube_url:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'No URL provided.'})
            }

        transcript, error = get_transcript(youtube_url)

        if error:
            return {
                'statusCode': 400,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': error})
            }

        summary = summarise(transcript)

        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'summary': summary})
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }

```

2\. Simple UI Frontend
----------------------

Because your backend logic will live in AWS Lambda, your UI only needs to be a lightweight frontend that makes HTTP requests to your AWS endpoint.

You could build a full web application using a framework like Django, but for a single-purpose tool, a static HTML page with Vanilla JavaScript is the most efficient approach. You can save this as `index.html` and run it locally in your browser.

HTML

```
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Summarizer</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; }
        input[type="text"] { width: 70%; padding: 10px; font-size: 16px; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 10px 20px; font-size: 16px; cursor: pointer; background-color: #007bff; color: white; border: none; border-radius: 4px; }
        button:disabled { background-color: #cccccc; }
        #result { margin-top: 30px; padding: 20px; background-color: #f8f9fa; border-radius: 8px; white-space: pre-wrap; display: none; }
        .loading { color: #666; font-style: italic; display: none; margin-top: 15px; }
    </style>
</head>
<body>

    <h2>YouTube Video Summarizer</h2>
    <div>
        <input type="text" id="urlInput" placeholder="Enter YouTube URL (e.g., https://www.youtube.com/watch?v=...)">
        <button id="submitBtn" onclick="summarizeVideo()">Summarize</button>
    </div>
    <div id="loading" class="loading">Fetching transcript and generating summary... this may take a few seconds.</div>
    <div id="result"></div>

    <script>
        // You will replace this with your actual AWS API Gateway URL once deployed
        const API_ENDPOINT = 'https://your-api-id.execute-api.region.amazonaws.com/prod/summarize';

        async function summarizeVideo() {
            const urlInput = document.getElementById('urlInput').value;
            const submitBtn = document.getElementById('submitBtn');
            const loading = document.getElementById('loading');
            const resultDiv = document.getElementById('result');

            if (!urlInput) {
                alert("Please enter a URL");
                return;
            }

            // Update UI state
            submitBtn.disabled = true;
            loading.style.display = 'block';
            resultDiv.style.display = 'none';
            resultDiv.innerHTML = '';

            try {
                const response = await fetch(API_ENDPOINT, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: urlInput })
                });

                const data = await response.json();

                if (response.ok) {
                    resultDiv.innerHTML = data.summary;
                } else {
                    resultDiv.innerHTML = `<span style="color:red">Error: ${data.error}</span>`;
                }
            } catch (error) {
                resultDiv.innerHTML = `<span style="color:red">Network Error: Could not reach the API.</span>`;
            } finally {
                // Restore UI state
                submitBtn.disabled = false;
                loading.style.display = 'none';
                resultDiv.style.display = 'block';
            }
        }
    </script>
</body>
</html>

```

3\. AWS Deployment Plan
-----------------------

To connect the UI to your script, you need to route requests from the open web to your Python code.

**1.Package Lambda Dependencies:**AWS doesn't have these libraries pre-installed.

Create a new directory for your project. Inside it, install your dependencies to the local folder using:

`pip install youtube-transcript-api openai -t .`

Place your refactored Python code into a file named `lambda_function.py` in the same directory. Zip the entire contents of the directory (not the directory itself).

**2.Create the Lambda Function:**

In the AWS Console, create a new Lambda function using the Python 3.12 runtime. Upload the `.zip` file you just created as the function's source code. Ensure the handler setting in AWS is set to `lambda_function.lambda_handler`.

**3.Configure Environment Variables:**

In the Lambda function's "Configuration" > "Environment variables" tab, add `OPENAI_API_KEY`, `OPENAI_ORG_ID`, and `OPENAI_PROJECT_ID`. Also, increase the function timeout (under "General configuration") from the default 3 seconds to at least 30 seconds, as LLM generation takes time.

**4.Set Up API Gateway:**Crucial: Enable CORS.

Navigate to API Gateway and create a new HTTP API. Add a route for `POST /summarize` and attach your Lambda function as the integration. Navigate to the CORS configuration for the API and add `*` (or your specific UI domain) to the "Access-Control-Allow-Origin" settings so your browser UI is permitted to call it.

**5.Connect and Deploy:**

Copy the "Invoke URL" from your API Gateway and paste it into the `API_ENDPOINT` variable in your `index.html` file. You can now open the HTML file locally or host it for free via GitHub Pages, AWS S3, or Vercel.