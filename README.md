# Serverless YouTube Summarizer (AWS Cloud-Native)

An end-to-end, serverless application that takes a YouTube URL, extracts its transcript, generates a structured summary using OpenAI's GPT-4o-mini, and caches the results in DynamoDB. The frontend is served globally via CloudFront from a private S3 bucket.

---

## 🏗️ System Architecture

```
[ User Browser ]
       │
       ▼
[ CloudFront CDN ] ──► [ S3 Bucket (Static UI: index.html, app.js) ]
       │
       ▼ (REST API Call)
[ AWS API Gateway ] (/summarize)
       │
       ▼
[ AWS Lambda (Python 3.13) ]
       ├──► [ SSM Parameter Store ] (Fetches OpenAI API Key)
       ├──► [ DynamoDB Cache ]      (Read/Write Summaries)
       ├──► [ Residential Proxy ]   (Bypasses YouTube IP Blocks) ──► [ YouTube API ]
       └──► [ OpenAI API ]          (GPT-4o-mini Summarization)
```

### Tech Stack
- **Frontend:** Static HTML5 / Modern JavaScript (`app.js`) hosted on S3 & distributed via CloudFront with OAC (Origin Access Control).
- **API Gateway:** REST API (`POST /summarize`) with CORS enabled.
- **Compute:** AWS Lambda running Python 3.13 (`x86_64` Amazon Linux runtime).
- **Database / Caching:** AWS DynamoDB (`youtube-summaries` table).
- **Secrets Management:** AWS SSM Parameter Store (`/youtube-summarizer/openai-api-key`).
- **External Integrations:**
  - `youtube-transcript-api` (v1.0.0+) with `GenericProxyConfig` support.
  - OpenAI API (`gpt-4o-mini`).
  - Residential Proxy Gateway (e.g., DataImpulse).

---

## ✨ Features

- **Cost-Optimized Caching:** Checks DynamoDB before making LLM or transcript calls, preventing duplicate API costs for previously summarized videos.
- **YouTube Cloud IP Bypass:** Integrates residential proxy routing to circumvent YouTube's anti-bot restrictions on AWS datacenter IP ranges.
- **Cross-Platform Lambda Packaging:** Uses Linux platform targeting (`manylinux2014_x86_64`) to eliminate native binary compatibility issues (e.g., `pydantic-core`).
- **Comprehensive Logging & Error Handling:** Full CloudWatch tracing across all external integration points (SSM, DynamoDB, Proxy, OpenAI).

---

## 📁 Repository Structure

```
.
├── src/
│   └── lambda_function.py    # Main AWS Lambda handler & business logic
├── build.sh                  # Automated cross-platform deployment packaging script
├── CONTEXT.md                # Infrastructure state and troubleshooting history
└── README.md                 # Project documentation
```

---

## ⚙️ Environment Variables & Configuration

### Lambda Environment Variables
| Variable Key | Description | Default / Example Value |
| :--- | :--- | :--- |
| `PROXY_URL` | Residential proxy gateway URL for YouTube requests | `http://USER:PASS@gw.dataimpulse.com:823` |
| `DYNAMODB_TABLE` | DynamoDB table name for cached summaries | `youtube-summaries` |
| `SSM_PARAM_NAME` | Parameter Store path for the OpenAI API Key | `/youtube-summarizer/openai-api-key` |

### SSM Parameter Store
- **Name:** `/youtube-summarizer/openai-api-key`
- **Type:** `SecureString`
- **Value:** `sk-proj-...`

---

## 🚀 Deployment Guide

### Prerequisites
- [AWS CLI](https://aws.amazon.com/cli/) configured with appropriate IAM permissions.
- [Python 3.13](https://www.python.org/) installed locally.
- An active [OpenAI API Key](https://platform.openai.com/).
- A residential proxy service (e.g., [DataImpulse](https://dataimpulse.com/)).

### 1. Provision Infrastructure
1. **SSM Parameter Store:** Create a `SecureString` parameter containing your OpenAI API Key named `/youtube-summarizer/openai-api-key`.
2. **DynamoDB:** Create a table named `youtube-summaries` with Partition Key `video_id` (`String`).
3. **IAM Role:** Assign `AmazonDynamoDBFullAccess` and `AmazonSSMReadOnlyAccess` policy permissions to your Lambda function's execution role.

### 2. Build Deployment Package
Run the automated packaging script to build a cross-compiled ZIP package for AWS Lambda:

```bash
chmod +x build.sh
./build.sh
```

This script:
- Cleans up existing build directories.
- Downloads dependencies targeting `manylinux2014_x86_64` for Python 3.13.
- Bundles `src/lambda_function.py` and library packages directly at the ZIP root.
- Generates `deployment.zip`.

### 3. Deploy to AWS Lambda
1. In the AWS Lambda Console, upload `deployment.zip` to your function (`youtube-summarizer`).
2. Configure environment variables (`PROXY_URL`, `DYNAMODB_TABLE`, `SSM_PARAM_NAME`).
3. Set Lambda function timeout to **30 seconds**.

### 4. API Gateway & Frontend Setup
1. Create a `POST /summarize` route in API Gateway with CORS enabled.
2. Deploy the API Gateway to a stage (e.g., `prod`).
3. Update `API_ENDPOINT` in `app.js` with your API Gateway full URL.
4. Upload frontend assets to S3 and invalidate/refresh CloudFront cache if applicable.

---

## 🔍 Troubleshooting & Lessons Learned

| Issue | Root Cause | Resolution |
| :--- | :--- | :--- |
| `ImportModuleError: pydantic_core` | Compiled C-extensions built on macOS/Windows differ from Lambda Linux binaries. | Used `--platform manylinux2014_x86_64` and `--only-binary=:all:` in `pip install`. |
| `YouTubeTranscriptApi has no attribute get_transcript` | `youtube-transcript-api` v1.0.0+ removed static methods. | Refactored code to instantiate class (`ytt_api = YouTubeTranscriptApi()`) and use `.fetch()`. |
| `IP Blocked / RequestBlocked` | YouTube blocks known AWS Cloud Provider IP ranges. | Routed requests through residential proxy via `GenericProxyConfig`. |
| `Unable to import module 'lambda_function'` | Dependencies wrapped in nested `package/` folder inside ZIP archive. | Updated build script to `cd package && zip -r ../deployment.zip .`. |

---

## 📜 License
Distributed under the MIT License.