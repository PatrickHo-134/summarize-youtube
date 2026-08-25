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
- **Problem:** Local build on macOS caused `ImportModuleError: No module named 'pydantic_core._pydantic_core'` on Lambda’s Linux environment.
- **Fix:** Built packaging using cross-platform Linux flags for Python 3.13:
  ```bash
  rm -rf package deployment.zip && mkdir package
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