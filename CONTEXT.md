# Project Context: YouTube Summarizer (AWS Cloud-Native)

## 1. Project Overview & Architecture

- **Goal:** Serverless full-stack web application that accepts a YouTube URL, fetches the transcript, generates a summary via OpenAI (GPT-4o-mini), and caches results in DynamoDB.
- **Monorepo Structure:** Clean separation between isolated serverless backend service (`/backend`) and modern React UI (`/frontend`).
- **Frontend Stack:** React 18, TypeScript, Vite, Tailwind CSS v4, `react-markdown`, `react-icons`, and `lucide-react`. Hosted in a private S3 bucket and distributed globally via AWS CloudFront.
- **Backend Stack:** AWS Lambda running Python 3.13 (`x86_64` / Amazon Linux) triggered by AWS API Gateway REST API (`POST /summarize`).
- **Storage & Config:** DynamoDB (`youtube-summaries` table for caching), AWS SSM Parameter Store (OpenAI API Key), Lambda Environment Variables (`PROXY_URL`).

---

## 2. Directory Layout

```
SUMMARIZE-YOUTUBE/
├── backend/                  # Isolated Python Lambda Service
│   ├── src/                  # Lambda source code (lambda_function.py)
│   ├── tests/                # Pytest unit & integration tests
│   ├── build.sh              # Cross-platform Linux packaging script
│   ├── requirements.txt      # Production dependencies (openai, youtube-transcript-api)
│   └── requirements-dev.txt  # Local dev/test dependencies
├── frontend/                 # Vite + React + TypeScript Frontend
│   ├── src/
│   │   ├── components/       # UrlForm.tsx, SummaryViewer.tsx, ActionControls.tsx
│   │   ├── hooks/            # useSummarize.ts (API state & retry management)
│   │   ├── types/            # index.ts (FetchStatus, SummarizeResponse)
│   │   ├── App.tsx           # Main application shell
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
- **API Gateway ID:** `etx5b18bqf`
  - Resource Path: `/summarize`
  - HTTP Method: `POST` (with `OPTIONS` enabled for CORS preflight).
  - Stage: `prod`
  - Full Endpoint URL: `https://etx5b18bqf.execute-api.ap-southeast-2.amazonaws.com/prod/summarize`
- **Lambda Function:** `youtube-summarizer`
  - Runtime: **Python 3.13** (`x86_64`)
  - Timeout: 30 seconds
  - IAM Roles: `AmazonDynamoDBFullAccess`, `AmazonSSMReadOnlyAccess`

---

## 4. Automation & Deployment Pipeline

### A. Frontend Deployment (`deploy-frontend.sh`)

Automates building Vite static assets, updating S3, and clearing CDN edge caches:

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

### B. Backend Deployment (`backend/build.sh`)

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
