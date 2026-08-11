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
