# Serverless YouTube Summarizer (AWS Cloud-Native)

![version](https://img.shields.io/badge/version-2.1.0-blue)

An end-to-end, serverless web application that accepts a YouTube URL, extracts its transcript, generates a structured summary using OpenAI's GPT-4o-mini, and caches the results in DynamoDB. The application features a modern React/TypeScript frontend distributed globally via CloudFront from a private S3 bucket.

---

## 🏗️ System Architecture

```
[ User Browser (Amplify Auth) ]
       │
       ▼
[ CloudFront CDN ] ──► [ S3 Bucket (Vite + React + TS Static Build) ]
       │
       ▼ (REST API Call + JWT Bearer Token)
[ AWS API Gateway ] (/summarize & /history with Cognito Authorizer)
       │
       ├──► [ AWS Lambda: youtube-summarizer (Python 3.13) ]
       │           ├──► [ SSM Parameter Store ] (Fetches OpenAI API Key)
       │           ├──► [ DynamoDB: summaries ] (Read/Write Global Cache)
       │           ├──► [ DynamoDB: users ]     (Write Ownership Mapping)
       │           ├──► [ S3: transcripts ]     (Fire-and-Forget Raw Storage)
       │           ├──► [ Residential Proxy ]   (Bypasses YouTube IP Blocks) ──► [ YouTube API ]
       │           └──► [ OpenAI API ]          (GPT-4o-mini Summarization)
       │
       └──► [ AWS Lambda: get-history (Python 3.13) ]
                   ├──► [ DynamoDB: users ]     (Read Ownership Mapping)
                   └──► [ DynamoDB: summaries ] (Read Cached Summaries)
```

### Tech Stack

- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS v4, `react-markdown`, `react-icons`, and `lucide-react`.
- **Authentication:** Amazon Cognito User Pools mapped via the AWS Amplify v6 `@aws-amplify/ui-react` SDK.
- **Hosting & Distribution:** Amazon S3 (Private Bucket) + CloudFront CDN with Origin Access Control (OAC).
- **API Gateway:** REST API (`POST /summarize` and `GET /history`) secured via Cognito Authorizer with CORS enabled.
- **Compute:** AWS Lambda running Python 3.13 (`x86_64` Amazon Linux runtime).
- **Database & Secrets:** AWS DynamoDB (`youtube-summaries` & `user-submissions` tables), Amazon S3 (`youtube-transcripts-cache-<env>` for raw transcripts), and AWS SSM Parameter Store (`/youtube-summarizer/openai-api-key`).
- **External Integrations:** `youtube-transcript-api` (v1.0.0+) with `GenericProxyConfig`, OpenAI API (`gpt-4o-mini`), DataImpulse Residential Proxy.

---

## ✨ Features

- **Progressive Engagement:** Employs "lazy registration" by allowing unauthenticated users to view the landing page and enter a URL. The system intercepts the submission and presents a styled auth modal only when an action is attempted.
- **Secure API & Content Tracking:** Blocks unauthorized backend requests at the edge via API Gateway. Maps individual `user_id` to `video_id` submissions in DynamoDB, ensuring content visibility boundaries and enabling user history lookups.
- **Beautiful Markdown Rendering:** Transforms LLM bullet points and headers into formatted HTML using `react-markdown`.
- **Cache Hit Indicator:** Real-time visual badge highlighting whether a summary was newly **Generated** via OpenAI or loaded instantly from the **Cached** DynamoDB store.
- **Cost-Optimized Caching:** Prevents duplicate LLM and proxy API costs by verifying cached video IDs in DynamoDB prior to execution.
- **Raw Data Retention:** Asynchronously archives raw JSON transcripts into an S3 bucket immediately after fetching. This bypasses DynamoDB's 400KB item limit for long podcasts and creates a permanent data asset for future features (like "Chat with Video") without incurring additional proxy costs.
- **Error & Retry Handling:** Displays inline error states and provides a **Retry Request** trigger when video transcripts fail or API limits are exceeded.
- **Email Sharing Action:** Allows users to export video takeaways directly to their default mail client via a single click.
- **YouTube Cloud IP Bypass:** Bypasses AWS datacenter IP restrictions imposed by YouTube using residential proxy routing.

---

## 📁 Repository Structure

```
SUMMARIZE-YOUTUBE/
├── backend/                  # Isolated Python Lambda Service
│   ├── summarize/            # youtube-summarizer Lambda
│   │   ├── src/              # Lambda handler & business logic
│   │   ├── tests/            # Unit & integration tests
│   │   ├── build.sh          # Cross-platform Linux packaging script
│   │   ├── requirements.txt  # Production dependencies
│   │   └── requirements-dev.txt  # Development dependencies
│   └── get_history/          # get-history Lambda
│       ├── src/              # lambda_function.py
│       ├── tests/            # Pytest unit tests
│       ├── build.sh          # Packaging script (no native deps)
│       └── requirements.txt  # Production dependencies (boto3)
├── frontend/                 # Vite + React + TypeScript App
│   ├── .env.local            # Local development config variables
│   ├── src/
│   │   ├── components/       # UrlForm.tsx, SummaryViewer.tsx, AuthModal.tsx
│   │   ├── hooks/            # Custom fetch & auth state hook (useSummarize.ts)
│   │   ├── services/         # Token handling module (auth.ts)
│   │   ├── types/            # TypeScript interface declarations
│   │   ├── App.tsx           # Main application layout
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── deploy-frontend.sh        # S3 Sync & CloudFront Invalidation automation
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
| `DYNAMODB_TABLE` | DynamoDB table name for cached summaries           | `youtube-summaries`                           |
| `SSM_PARAM_NAME` | Parameter Store path for the OpenAI API Key        | `/youtube-summarizer/openai-api-key` |
| `USER_SUBMISSIONS_TABLE` | Mapping table for user authentication limits | `user-submissions` |
| `TRANSCRIPT_BUCKET` | S3 bucket name for caching raw transcript data | `youtube-transcripts-cache-prod` |
| `YOUTUBE_SUMMARIES_TABLE` | DynamoDB table name for cached summaries (get-history) | `youtube-summaries` |
| `CORS_ALLOW_ORIGIN` | Allowed origin for CORS headers (get-history) | `*` |

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
```

#### Run tests

```bash
# youtube-summarizer tests
backend/venv/bin/python -m pytest backend/summarize/tests/test_lambda_function.py -v

# get-history tests
backend/venv/bin/python -m pytest backend/get_history/tests/test_lambda_function.py -v
```

---

### 3\. Backend Lambda Build & Deployment

#### Package for AWS Lambda

Run the cross-platform packaging script inside the `backend/` directory:

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

#### Deploy Zip to Lambda

Upload the generated `deployment.zip` to the appropriate Lambda function (`youtube-summarizer` or `get-history`) via the AWS Lambda Console or AWS CLI.

## 🔍 Troubleshooting & Lessons Learned

| **Issue** | **Cause** | **Resolution** |
| --------- | --------- | -------------- |
|`IP Blocked / RequestBlocked`| YouTube blocks known AWS datacenter IP ranges.| Routed transcript requests through residential proxies via `GenericProxyConfig`. |

## 📜 License
Distributed under the MIT License.