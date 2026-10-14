# Serverless YouTube Summarizer (AWS Cloud-Native)

![version](https://img.shields.io/badge/version-3.2.0-blue)
[![Live Demo](https://img.shields.io/badge/Live_App-youtubesummary.patrickho.dev-4f46e5)](https://youtubesummary.patrickho.dev)

An end-to-end, serverless web application that accepts a YouTube URL, extracts its transcript, generates a structured summary using OpenAI's GPT-4o-mini, and caches the results in DynamoDB. The application features a modern React/TypeScript frontend distributed globally via CloudFront from a private S3 bucket and mapped to a custom domain via Cloudflare.

**Live Application:** [https://youtubesummary.patrickho.dev](https://youtubesummary.patrickho.dev)

---

## 🏗️ Architecture & Asynchronous Flow

1. **Job Submission (`POST /summarize`)**:
   - The React frontend sends a YouTube video ID with a valid Cognito JWT.
   - The `summarization-job-producer` Lambda generates a unique `job_id`, records an initial `PENDING` state in the `summarization-jobs` DynamoDB table, and pushes the payload to an **Amazon SQS queue**.
   - Returns an HTTP `202 Accepted` response immediately with `{ job_id, status: "PENDING" }`.

2. **Background Processing (SQS Worker)**:
   - An SQS event triggers the `youtube-summarizer` Lambda worker.
   - The worker fetches the transcript, communicates with the OpenAI API, stores raw transcripts in a private S3 cache bucket, caches global results in `youtube-summaries`, and updates the job status (`COMPLETED` or `FAILED`) in DynamoDB.

3. **Status Polling (`GET /jobs/{job_id}`)**:
   - The frontend enters a polling interval (every 2.5 seconds) calling the `get-summarization-job` Lambda.
   - Once status returns `COMPLETED`, the polling clears, and the markdown summary and video title are rendered instantly.

```
[ User Browser (Amplify Auth) ]
       │
       ▼
[ Cloudflare DNS & WAF ]
       │
       ▼
[ CloudFront CDN ] ──► [ S3 Bucket (Vite + React + TS Static Build) ]
       │
       ▼ (REST API Call + JWT Bearer Token)
[ AWS API Gateway ] (/summarize, /jobs/{job_id}, & /history with Cognito Authorizer)
       │
       ├──► [ AWS Lambda: summarization-job-producer (POST /summarize) ]
       │           └──► [ Amazon SQS Queue ] ──► [ AWS Lambda: youtube-summarizer (Worker) ]
       │                       ├──► [ SSM Parameter Store ] (Fetches OpenAI API Key)
       │                       ├──► [ DynamoDB: summaries ] (Read/Write Global Cache)
       │                       ├──► [ DynamoDB: jobs ]      (Task State Tracking)
       │                       ├──► [ DynamoDB: users ]     (Write Ownership Mapping)
       │                       ├──► [ S3: transcripts ]     (Fire-and-Forget Raw Storage)
       │                       ├──► [ Residential Proxy ]   (Bypasses YouTube IP Blocks) ──► [ YouTube API ]
       │                       └──► [ OpenAI API ]          (GPT-4o-mini Summarization)
       │
       ├──► [ AWS Lambda: get-summarization-job (GET /jobs/{job_id}) ]
       │           └──► [ DynamoDB: jobs ]          (Query Task Status & Result)
       │
       └──► [ AWS Lambda: get-history (GET /history) ]
       ├──► [ DynamoDB: users ]     (Read Ownership Mapping)
       └──► [ DynamoDB: summaries ] (Read Cached Summaries)
```

### Tech Stack

- **Frontend Hosting:** Amazon S3 (private bucket with Origin Access Control) distributed globally via **Amazon CloudFront**.
- **Authentication:** Amazon Cognito User Pools (SPA configuration without client secret) providing secure JWT tokens.
- **API Gateway REST API:**
  - Protected by a Cognito User Pool Authorizer.
  - Stage variables (`envAlias`) dynamically route requests to either `dev` or `prod` Lambda aliases.
  - Endpoints:
    - `POST /summarize` (Producer)
    - `GET /jobs/{job_id}` (Polling status check)
    - `GET /history` (Saved user summaries library)
- **DynamoDB Tables:**
  - `summarization-jobs`: Tracks asynchronous task lifecycle (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`), results, and error messages.
  - `youtube-summaries`: Global cache for video summaries to minimize redundant LLM costs.
  - `user-submissions`: Mapping table enforcing user ownership and library pagination.

---

## ✨ Features

- **Asynchronous Task Architecture:** Offloads long-running transcript fetching and LLM calls to background SQS workers, ensuring immediate `202 Accepted` responses and zero API Gateway timeout errors.
- **Real-Time Frontend Polling:** Features a state machine in the React client that polls job progress and transitions smoothly through loading, completion, or failure states.
- **Progressive Engagement:** Employs "lazy registration" by allowing unauthenticated users to view the landing page and enter a URL. The system intercepts the submission and presents a styled auth modal only when an action is attempted.
- **Secure API & Content Tracking:** Blocks unauthorized backend requests at the edge via API Gateway. Maps individual `user_id` to `video_id` submissions in DynamoDB, ensuring content visibility boundaries and enabling user history lookups.
- **Beautiful Markdown Rendering:** Transforms LLM bullet points and headers into formatted HTML using `react-markdown`.
- **Cache Hit Indicator:** Real-time visual badge highlighting whether a summary was newly **Generated** via OpenAI or loaded instantly from the **Cached** DynamoDB store.
- **Cost-Optimized Caching:** Prevents duplicate LLM and proxy API costs by verifying cached video IDs in DynamoDB prior to execution.
- **Raw Data Retention:** Asynchronously archives raw JSON transcripts into an S3 bucket immediately after fetching. This bypasses DynamoDB's 400KB item limit for long podcasts and creates a permanent data asset for future features without incurring additional proxy costs.
- **Error & Retry Handling:** Displays inline error states and provides a **Retry Request** trigger when video transcripts fail or API limits are exceeded.
- **Email Sharing Action:** Allows users to export video takeaways directly to their default mail client via a single click.
- **YouTube Cloud IP Bypass:** Bypasses AWS datacenter IP restrictions imposed by YouTube using residential proxy routing.
- **Paginated History Dashboard:** Utilizes DynamoDB cursor-based pagination (`LastEvaluatedKey`) to fetch user history efficiently. The frontend seamlessly handles these cursors via a "Load More" interface, ensuring fast load times and minimal memory consumption even for users with hundreds of saved summaries.

---

## 📁 Repository Structure

```
SUMMARIZE-YOUTUBE/
├── backend/                  # Isolated Python Lambda Services
│   ├── producer/             # summarization-job-producer Lambda (POST /summarize)
│   │   ├── src/              # lambda_function.py
│   │   └── requirements.txt  # boto3
│   ├── summarizer/           # youtube-summarizer SQS Worker Lambda
│   │   ├── src/              # lambda_function.py (OpenAI & transcript processing)
│   │   ├── build.sh          # Cross-platform Linux packaging script
│   │   └── requirements.txt  # openai, youtube-transcript-api, boto3
│   ├── get_job/              # get-summarization-job Lambda (GET /jobs/{job_id})
│   │   ├── src/              # lambda_function.py
│   │   └── requirements.txt  # boto3
│   └── get_history/          # get-history Lambda (GET /history)
│       └── src/              # lambda_function.py
├── frontend/                 # Vite + React + TypeScript Frontend
│   ├── src/                  # Components, hooks, services, and types
│   ├── package.json
│   └── vite.config.ts
├── deploy-frontend.sh        # S3 sync & CloudFront cache invalidation script
├── CONTEXT.md                # Infrastructure state and troubleshooting history
└── README.md                 # Project documentation
```

---

## ⚙️ Environment Variables & Configuration

### Frontend React/Vite Variables (`frontend/.env.production`)

| **Variable Key** | **Description** | **Example Value** |
| --- | --- | --- |
| `VITE_COGNITO_USER_POOL_ID` | Cognito User Directory Identifier | `us-east-1_XXXXXXXXX` |
| `VITE_COGNITO_USER_POOL_CLIENT_ID` | SPA App Client ID (Without secret) | `XXXXXXXXXXXXXXXXXXXXXXXXXX` |
| `VITE_API_ENDPOINT` | Production API Gateway path | `https://etx5.../prod` |

### Backend Lambda Environment Variables

| Variable Key     | Description                                        | Default / Example Value                       |
| :--------------- | :------------------------------------------------- | :-------------------------------------------- |
| `PROXY_URL`      | Residential proxy gateway URL for YouTube requests | `http://USER:PASS@gw.dataimpulse.com:823`     |
| `YOUTUBE_SUMMARIES_TABLE` | DynamoDB table name for cached summaries  | `youtube-summaries`                           |
| `SUMMARIZATION_JOBS_TABLE` | DynamoDB table name tracking async task state and results | `summarization-jobs` |
| `SSM_PARAM_NAME` | Parameter Store path for the OpenAI API Key        | `/youtube-summarizer/openai-api-key` |
| `USER_SUBMISSIONS_TABLE` | Mapping table for user authentication limits | `user-submissions` |
| `TRANSCRIPT_BUCKET` | S3 bucket name for caching raw transcript data | `youtube-transcripts-cache-prod` |
| `CORS_ALLOW_ORIGIN` | Allowed origin for CORS headers (get-history) | `*` |
| `SQS_QUEUE_URL` | SQS queue URL used by the producer Lambda in **prod** | `https://sqs.ap-southeast-2.amazonaws.com/.../queue-prod` |
| `SQS_QUEUE_URL_DEV` | SQS queue URL used by the producer Lambda in **dev** | `https://sqs.ap-southeast-2.amazonaws.com/.../queue-dev` |
| `ENVIRONMENT` | Deployment environment for the producer Lambda; controls which SQS URL is used | `dev` or `prod` |

---

## 🚀 Development & Deployment Guide

### Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) configured with valid IAM access credentials.
- [Node.js (v18+)](https://nodejs.org/) & `npm` installed locally.
- [Python 3.13](https://www.python.org/) installed locally.

---

### 1. Frontend Local Development & Deployment

#### Run Locally

```bash
cd frontend
npm install
npm run dev
```

#### Deploy to AWS (S3 + CloudFront)

Make sure deploy-frontend.sh is executable, then run it from the root directory:

```Bash
chmod +x deploy-frontend.sh
./deploy-frontend.sh
```

This script compiles production assets (npm run build), syncs the dist/ directory to S3, and invalidates the CloudFront CDN cache.

### 2\. Backend Unit Tests

#### First-time setup (creates venv and installs dev dependencies)

```bash
python3.13 -m venv backend/venv
backend/venv/bin/pip install -r backend/summarize/requirements-dev.txt
backend/venv/bin/pip install -r backend/job_status/requirements-dev.txt
```

#### Run tests

```bash
# youtube-summarizer tests
backend/venv/bin/python -m pytest backend/summarize/tests/test_lambda_function.py -v

# get-history tests
backend/venv/bin/python -m pytest backend/get_history/tests/test_lambda_function.py -v

# job-status tests (uses moto to mock DynamoDB)
backend/venv/bin/python -m pytest backend/job_status/tests/test_lambda_function.py -v
```

> **Note:** Each Lambda's test suite must be run individually (as shown above). Running multiple `tests/test_lambda_function.py` files together in a single `pytest` invocation will fail due to duplicate module basenames across packages.

---

### 3\. Backend Lambda Build & Deployment

#### Package `summarize` for AWS Lambda

```Bash
cd backend/summarize
chmod +x build.sh
./build.sh
```

This script downloads Linux binaries (`manylinux2014_x86_64`) targeting Python 3.13 and bundles `src/lambda_function.py` into `deployment.zip`.

#### Package `get-history` for AWS Lambda

```bash
cd backend/get_history
chmod +x build.sh
./build.sh
```

Pure-Python; no cross-compilation needed. Bundles `src/` into `deployment.zip`.

#### Package `producer` for AWS Lambda

Before building, ensure the correct `SQS_QUEUE_URL` environment variable is set on the target Lambda function in AWS:

- **dev:** the Lambda's `ENVIRONMENT` variable must be `dev` and `SQS_QUEUE_URL_DEV` must point to the dev SQS queue.
- **prod:** the Lambda's `ENVIRONMENT` variable must be `prod` and `SQS_QUEUE_URL` must point to the prod SQS queue.

Then run the build script with the target environment:

```bash
cd backend/producer
chmod +x build.sh

# For dev (default)
./build.sh
# or explicitly:
./build.sh dev

# For prod
./build.sh prod
```

This produces `deployment-dev.zip` or `deployment-prod.zip` respectively. Upload the appropriate zip to the producer Lambda function via the AWS Lambda Console or AWS CLI.

#### Deploy Zip to Lambda

Upload the generated zip file to the appropriate Lambda function (`youtube-summarizer`, `producer`, or `get-history`) via the AWS Lambda Console or AWS CLI.

## 🔍 Troubleshooting & Lessons Learned

| **Issue** | **Cause** | **Resolution** |
| --------- | --------- | -------------- |
|`IP Blocked / RequestBlocked`| YouTube blocks known AWS datacenter IP ranges.| Routed transcript requests through residential proxies via `GenericProxyConfig`. |

## 📜 License
Distributed under the MIT License.