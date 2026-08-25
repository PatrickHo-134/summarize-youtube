# Project Context: YouTube Summarizer (AWS Cloud-Native)

## 1. Project Overview & Architecture
- **Goal:** Serverless full-stack web application that takes a YouTube URL, retrieves the transcript, and generates a summary using OpenAI's API (caching results in DynamoDB).
- **Frontend:** Static UI (`index.html`, `app.js`) hosted in a private S3 bucket and served globally via AWS CloudFront over HTTPS.
- **API Layer:** AWS API Gateway (REST API) routing requests to AWS Lambda.
- **Backend:** AWS Lambda function written in Python 3.13 running on `x86_64` (Amazon Linux environment).
- **Storage & Config:** DynamoDB (caching), AWS SSM Parameter Store (OpenAI API keys).

---

## 2. Resource & Endpoint Configuration
- **CloudFront Domain:** `https://d1lixi6ffoheyhp.cloudfront.net`
  - Access control: Origin Access Control (OAC) targeting private S3 bucket.
  - Default Root Object: `index.html`
  - WAF/Security Protections: Disabled (to avoid additional monthly fees).
- **API Gateway ID:** `etx5b18bqf`
  - Resource Path: `/summarize`
  - HTTP Method: `POST` (with `OPTIONS` enabled for CORS preflight).
  - Stage: `prod`
  - Full Endpoint URL: `https://etx5b18bqf.execute-api.ap-southeast-2.amazonaws.com/prod/summarize`
- **Lambda Function:** `youtube-summarizer`
  - Runtime: **Python 3.13** (Architecture: `x86_64`)
  - Timeout: Set to 30 seconds.
  - IAM Permissions: `AmazonDynamoDBFullAccess`, `AmazonSSMReadOnlyAccess`.

---

## 3. Issues Debugged & Resolved

### A. Missing `boto3` in Pytest
- **Cause:** Terminal executed pytest inside the global Anaconda environment rather than the active virtualenv.
- **Fix:** Deactivated Conda (`conda deactivate`) or installed dependencies inside the target environment.

### B. CORS / 502 Bad Gateway Errors
- **Issue 1 (Wrong Endpoint):** `app.js` was hitting `/prod` instead of `/prod/summarize`.
  - *Fix:* Appended `/summarize` to the `API_ENDPOINT` string.
- **Issue 2 (`ImportModuleError: No module named 'pydantic_core._pydantic_core'`):**
  - *Cause:* Dependencies were installed on macOS, causing binary mismatches (C extensions) when executed on Lambda's Amazon Linux environment.
  - *Fix:* Re-packaged dependencies targeting Linux binaries via `pip`:
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

---

## 4. Current State & Immediate Next Step
- Updated `deployment.zip` compiled for Amazon Linux & Python 3.13.
- Reuploaded the new `.zip` package to the `youtube-summarizer` Lambda function in the AWS Console and test end-to-end functionality from the CloudFront UI.