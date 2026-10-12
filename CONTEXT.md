# Project Context: YouTube Summarizer (AWS Cloud-Native)

## 1. Project Overview & Architecture

- **Goal:** Serverless full-stack web application that accepts a YouTube URL, triggers an **asynchronous background job** via SQS, processes transcripts via OpenAI (GPT-4o-mini), and caches results in DynamoDB. The frontend handles job progression smoothly via background status polling (`GET /jobs/{job_id}`).
- **Authentication & Security:** Amazon Cognito User Pools provide secure JWT-based authentication. API Gateway REST API routes are protected by a Cognito Authorizer, with explicit `OPTIONS` preflight bypasses configured to eliminate CORS loops.
- **Monorepo Structure:** Clean separation between the isolated serverless backend service (`/backend`) and the React UI (`/frontend`).
- **Frontend Stack:**
  - React 18, TypeScript, Vite, Tailwind CSS v4, `react-markdown`, `react-icons`, and `lucide-react`.
  - Uses AWS Amplify v6 and `@aws-amplify/ui-react` for auth modal overlays.
  - Features tabbed navigation between the central URL summarizer landing hero (with asynchronous polling state machine) and a personal "Saved Summaries" dashboard library (`HistoryList`).
  - Hosted in a private S3 bucket and distributed globally via AWS CloudFront.
- **Backend Stack:** AWS Lambda running Python 3.13 (`x86_64` / Amazon Linux) triggered by AWS API Gateway REST API and Amazon SQS.
- **Storage & Config:** DynamoDB (`youtube-summaries` for global caching, `summarization-jobs` for tracking async background task states, and `user-submissions` mapping table) and Amazon S3 (private bucket for raw transcript bulk storage). AWS SSM Parameter Store stores the OpenAI API Key securely.

---

## 2. Directory Layout

```
SUMMARIZE-YOUTUBE/
├── backend/                  # Isolated Python Lambda Services
│   ├── producer/             # summarization-job-producer Lambda (POST /summarize)
│   │   ├── src/              # lambda_function.py
│   │   └── requirements.txt  # boto3, aws-lambda-powertools, etc.
│   ├── summarizer/           # youtube-summarizer SQS Worker Lambda
│   │   ├── src/              # lambda_function.py (processes SQS events & calls OpenAI)
│   │   └── requirements.txt  # openai, youtube-transcript-api, boto3
│   ├── get_job/              # get-summarization-job Lambda (GET /jobs/{job_id})
│   │   ├── src/              # lambda_function.py
│   │   └── requirements.txt  # boto3
│   └── get_history/          # get-history Lambda (GET /history)
│       └── src/              # lambda_function.py
├── frontend/                 # Vite + React + TypeScript Frontend
│   ├── .env.local            # Local development frontend configuration (.env)
│   ├── .env.production       # Static build configuration for CI/CD or deployment
│   ├── src/
│   │   ├── components/       # UrlForm.tsx, SummaryViewer.tsx, ActionControls.tsx, AuthModal.tsx, Navbar.tsx, Dashboard.tsx, SummaryCard.tsx, HistoryList.tsx
│   │   ├── hooks/            # useSummarize.ts (Async job submission & polling loop state management)
│   │   ├── services/         # api.ts, auth.ts
│   │   ├── types/            # index.ts (JobStatus, SummarizeResponse, HistoryItem)
│   │   ├── App.tsx           # Main application shell & tab router ('new' | 'dashboard')
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── deploy-frontend.sh        # S3 sync & CloudFront cache invalidation script
├── CONTEXT.md                # Infrastructure state and troubleshooting history
└── README.md                 # Project documentation
```

---

## 3. Infrastructure & Endpoint Configuration

- **CloudFront Domain:** `https://d1lixi6ffoheyhp.cloudfront.net`
  - Access Control: Origin Access Control (OAC) targeting private S3 bucket.
  - Default Root Object: `index.html`
- **Amazon Cognito (Authentication):** Configured as a Single-page application (SPA) without a client secret.
- **API Gateway ID:** `etx5b18bqf`
  - **Stages:** `dev` and `prod` (managed dynamically via stage variable `envAlias`).
  - **Endpoints:**
    1. `POST /summarize` → Routed to `summarization-job-producer:${stageVariables.envAlias}`. Returns `202 Accepted` with `{ job_id, status: "PENDING" }`.
    2. `GET /jobs/{job_id}` → Routed to `get-summarization-job:${stageVariables.envAlias}`. Returns current job status (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`) and result payload.
    3. `GET /history` → Routed to `get-history`. Protected by Cognito Authorizer.
  - **CORS & Auth:** Cognito User Pool Authorizer protects protected routes; `OPTIONS` methods are configured with `NONE` authorization to prevent preflight `401` CORS errors.
- **Lambda Functions:**
  - **`summarization-job-producer`**: Validates incoming request, generates unique `job_id`, records initial `PENDING` state in DynamoDB, and pushes message to SQS queue.
  - **`youtube-summarizer` (SQS Worker)**: Consumes SQS queue events, fetches transcripts, interacts with OpenAI API, caches results in `youtube-summaries`, and updates task state (`COMPLETED` / `FAILED`) in `summarization-jobs`.
  - **`get-summarization-job`**: Queries the `summarization-jobs` table using the `#res` alias to safely handle the reserved keyword `result`.
  - **`get-history`**: Queries paginated submission records.
- **DynamoDB Tables:**
    *   `summarization-jobs` (Partition Key: `job_id`): Tracks asynchronous job states (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`), error messages, and results.
    *   `youtube-summaries` (Partition Key: `video_id`): Preserves global LLM caching.
    *   `user-submissions` (Partition Key: `user_id`, Sort Key: `video_id`): Enforces content ownership.
- **Lambda Aliases:** `dev` and `prod` aliases are configured on all backend functions to cleanly isolate testing from production deployments.

---

## 4. Automation & Deployment Pipeline

### A. Frontend Deployment (`deploy-frontend.sh`)

Automates building Vite static assets, updating S3, and clearing CDN edge caches. The process hardcodes `.env.production` variables directly into the compiled JavaScript bundle for CloudFront distribution.

```bash
#!/bin/bash
set -e

S3_BUCKET="your-s3-bucket-name"
DISTRIBUTION_ID="your-cloudfront-distribution-id"

cd frontend
npm run build
aws s3 sync dist/ "s3://${S3_BUCKET}" --delete
aws cloudfront create-invalidation --distribution-id "${DISTRIBUTION_ID}" --paths "/*"
```

### B. Backend Deployment

#### `youtube-summarizer` Lambda (`backend/summarize/build.sh`)

For production rollouts, publish new versions and update stage aliases (`prod`):

```
aws lambda publish-version --function-name summarization-job-producer
aws lambda publish-version --function-name youtube-summarizer
aws lambda publish-version --function-name get-summarization-job

aws lambda update-alias --function-name summarization-job-producer --name prod --function-version <VERSION>
aws lambda update-alias --function-name youtube-summarizer --name prod --function-version <VERSION>
aws lambda update-alias --function-name get-summarization-job --name prod --function-version <VERSION>
```
