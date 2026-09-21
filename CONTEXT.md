# Project Context: YouTube Summarizer (AWS Cloud-Native)

## 1. Project Overview & Architecture

- **Goal:** Serverless full-stack web application that accepts a YouTube URL, fetches the transcript, generates a summary via OpenAI (GPT-4o-mini), and caches results in DynamoDB. The system now utilizes Amazon Cognito User Pools for identity management, providing secure JWT-based authentication.
- **Monorepo Structure:** Clean separation between isolated serverless backend service (`/backend`) and modern React UI (`/frontend`).
- **Frontend Stack:**
  - React 18, TypeScript, Vite, Tailwind CSS v4, `react-markdown`, `react-icons`, and `lucide-react`.
  - Uses AWS Amplify v6 and `@aws-amplify/ui-react` for auth modal overlays.
  - Features tabbed navigation between the central URL summarizer landing hero and a personal "Saved Summaries" dashboard library (`HistoryList`).
  - Hosted in a private S3 bucket and distributed globally via AWS CloudFront.
- **Backend Stack:** AWS Lambda running Python 3.13 (`x86_64` / Amazon Linux) triggered by AWS API Gateway REST API. Two Lambda functions: `youtube-summarizer` (`POST /summarize`) and `get-history` (`GET /history`). Both APIs are strictly protected by a Cognito User Pool Authorizer.
- **Storage & Config:** DynamoDB (`youtube-summaries` table for fast caching, and `user-submissions` mapping table) and Amazon S3 (private bucket for raw transcript bulk storage). AWS SSM Parameter Store stores the OpenAI API Key securely. Lambda Environment Variables include `PROXY_URL`, `USER_SUBMISSIONS_TABLE`, and `TRANSCRIPT_BUCKET`.

---

## 2. Directory Layout

```
SUMMARIZE-YOUTUBE/
├── backend/                  # Isolated Python Lambda Service
│   ├── summarize/            # youtube-summarizer Lambda
│   │   ├── src/              # Lambda source code (lambda_function.py)
│   │   ├── tests/            # Pytest unit & integration tests
│   │   ├── build.sh          # Cross-platform Linux packaging script
│   │   ├── requirements.txt  # Production dependencies (openai, youtube-transcript-api)
│   │   └── requirements-dev.txt  # Local dev/test dependencies
│   └── get_history/          # get-history Lambda
│       ├── src/              # lambda_function.py (GET /history handler)
│       ├── tests/            # Pytest unit tests
│       ├── build.sh          # Packaging script (no native deps)
│       └── requirements.txt  # Production dependencies (boto3)
├── frontend/                 # Vite + React + TypeScript Frontend
│   ├── .env.local            # Local development frontend configuration
│   ├── .env.production       # Static build configuration for CI/CD or deployment
│   ├── src/
│   │   ├── components/       # UrlForm.tsx, SummaryViewer.tsx, ActionControls.tsx, AuthModal.tsx, Navbar.tsx, Dashboard.tsx, SummaryCard.tsx, HistoryList.tsx
│   │   ├── hooks/            # useSummarize.ts (API state, auth checks, & retry management)
│   │   ├── services/         # auth.ts (Token fetching and auth state helpers)
│   │   ├── types/            # index.ts (FetchStatus, SummarizeResponse, HistoryItem)
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
- **Amazon Cognito (Authentication):** Configured as a Single-page application (SPA) without a client secret to support the browser-based Vite application securely.
- **API Gateway ID:** `etx5b18bqf`
  - Resource Path: `/summarize`
  - HTTP Method: `POST` (with `OPTIONS` enabled for CORS preflight).
  - Edge Protection: A Cognito User Pool Authorizer (`Cognito-Summarizer-Auth`) validates tokens automatically before requests reach the backend
  - Stage: `prod`
  - Full Endpoint URL: `https://etx5b18bqf.execute-api.ap-southeast-2.amazonaws.com/prod/summarize`
- **Lambda Function:** `youtube-summarizer`
  - Runtime: **Python 3.13** (`x86_64`)
  - Timeout: 30 seconds
  - Authorization Extraction: Extracts the authenticated user's unique identifier (`sub` claim) passed securely from API Gateway to enforce data ownership
  - IAM Roles: `AmazonDynamoDBFullAccess`, `AmazonSSMReadOnlyAccess`, and `s3:PutObject` (targeting the transcript cache bucket)
- **Lambda Function:** `get-history`
  - Runtime: **Python 3.13** (`x86_64`)
  - Timeout: 30 seconds
  - Triggered by: `GET /history` on the same API Gateway, protected by the same Cognito Authorizer
  - Logic: Queries `user-submissions` by `user_id` (`sub` claim), batch-fetches `title` and `summary` from `youtube-summaries`, and returns items sorted newest-first
  - IAM Roles: `AmazonDynamoDBFullAccess`
  - Environment Variables: `USER_SUBMISSIONS_TABLE`, `YOUTUBE_SUMMARIES_TABLE`, `CORS_ALLOW_ORIGIN`
  - Packaging: `backend/get_history/build.sh` (pure-Python, no cross-compilation needed)
- **DynamoDB Tables:**
    *   `youtube-summaries` (Partition Key: `video_id`): Preserves global LLM caching to prevent duplicate OpenAI and proxy costs
    *   `user-submissions` (Partition Key: `user_id`, Sort Key: `video_id`): Enforces content ownership and provides intrinsic support for future user history features
- **S3 Storage:**
    *   `youtube-transcripts-cache-<env>`: A private bucket that stores the raw JSON transcript payloads (`transcripts/{video_id}.json`) immediately after a successful fetch.

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

Cross-compiles Linux C-extensions (manylinux2014_x86_64) for Lambda Python 3.13:

```
#!/bin/bash
set -e
rm -rf package deployment.zip
mkdir -p package
pip install \
  --platform manylinux2014_x86_64 \
  --target=./package \
  --implementation cp \
  --python-version 3.13 \
  --only-binary=:all: --upgrade \
  youtube-transcript-api openai
cp src/lambda_function.py package/
cd package && zip -r ../deployment.zip . && cd ..
```

#### `get-history` Lambda (`backend/get_history/build.sh`)

Pure-Python; no cross-compilation required. Packages `src/` directly into `deployment.zip`:

```bash
cd backend/get_history
chmod +x build.sh
./build.sh
```

## 5\. Key Issues Resolved & Solutions

### 5.1 Endpoint Path & CORS (502 / Preflight Failures)

- **Problem:** `app.js` called `/prod` instead of `/prod/summarize`, causing CORS headers to be missed.

- **Fix:** Set `API_ENDPOINT` to `https://etx***.execute-api.ap-southeast-2.amazonaws.com/prod/summarize` and redeployed API Gateway stage `prod`.

### 5.2 Binaries Mismatch (`pydantic_core`)

- **Problem:** Local build on macOS caused `ImportModuleError: No module named 'pydantic_core._pydantic_core'` on Lambda's Linux environment.

- **Fix:** Built packaging using cross-platform Linux flags `--platform manylinux2014_x86_64` for Python 3.13.

### 5.3 AWS Datacenter IP Block by YouTube

- **Problem:** YouTube blocked transcript requests originating from AWS cloud provider IP ranges.

- **Fix:** Integrated residential proxies (DataImpulse) injected through the `PROXY_URL` environment variable via `GenericProxyConfig`.

### 5.4 Frontend UI Modernization & Monorepo Migration

- **Problem:** Legacy single `index.html` rendered raw unformatted Markdown string output without interactive retry or mailing options.

- **Fix:** Migrated to React/TypeScript inside `/frontend`. Utilized `react-markdown` for structured HTML rendering, added a cache hit indicator badge, implemented a `mailto:` email summary trigger, and created a retry action button on API failure.

### 5.5 Minimalist UI Redesign & Dashboard Library (`HistoryList`)

-   **Problem:** The interface lacked structured navigation and a dedicated library view to explore previously summarized videos.

-   **Fix:** Redesigned the UI using Tailwind CSS v4 and `lucide-react`. Built `Navbar.tsx` for seamless tab switching ("New Summary" vs "Dashboard"), updated `UrlForm.tsx` with a centered pill-style input hero section, and created `HistoryList.tsx` to render saved summaries as structured cards with date badges and "Newest/Oldest first" sorting.


### 5.6 History Page — Dedicated `get-history` Lambda

-   **Problem:** The Dashboard (`HistoryList`) needed a dedicated backend endpoint to retrieve a user's previously summarized videos, joining data across two DynamoDB tables (`user-submissions` and `youtube-summaries`).

-   **Fix:** Created a standalone Lambda function (`backend/get_history/`) that authenticates via the `sub` Cognito claim, queries `user-submissions` by `user_id`, batch-fetches `video_id`, `title`, and `summary` from `youtube-summaries`, and returns a CORS-safe JSON response sorted newest-first. The function has its own `build.sh` (no native deps) and Pytest test suite.

### 5.7 Raw Transcript Caching & DynamoDB Constraints

- **Problem:** DynamoDB imposes a strict 400 KB maximum item size limit. Storing raw transcripts for long videos (e.g., 2+ hour podcasts) directly in the `youtube-summaries` table risked triggering `ValidationException` errors. Furthermore, lacking a permanent raw data asset required unnecessary re-fetching for future features (like generating different summary lengths).
- **Fix:** Implemented a hybrid storage strategy. The `youtube-summarizer` Lambda now executes a fire-and-forget S3 upload of the raw transcript JSON to a dedicated bucket (`youtube-transcripts-cache-prod`) immediately after a successful proxy fetch. DynamoDB remains the fast-access cache for the concise OpenAI summaries. If the S3 upload fails (e.g., IAM issue), it logs the error and gracefully proceeds to LLM generation so the end user is not interrupted.
