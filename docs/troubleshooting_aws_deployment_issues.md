Troubleshooting & Architecture Post-Mortem: Serverless Async YouTube Summarizer
===============================================================================

This document outlines the core technical challenges, root causes, and resolutions encountered while implementing and deploying the asynchronous, event-driven YouTube Summarizer architecture (API Gateway, Amazon SQS, AWS Lambda, and DynamoDB).

1\. API Gateway `404 Not Found` Errors
--------------------------------------

### Symptom

Testing the newly added job status endpoint (`GET /jobs/{job_id}`) returned a `404 Not Found` response, even though the path appeared correct in code and documentation.

### Root Cause

1.  **Un-deployed API Changes:** In API Gateway, adding new resources or methods does not make them live automatically; they require an explicit stage deployment.

2.  **Missing Stage Variables:** The Lambda integration was configured to use dynamic stage aliases via `${stageVariables.envAlias}`. If the `envAlias` stage variable was missing from the target stage (`dev` or `prod`), API Gateway failed to resolve the backend target and dropped the request.

### Resolution

-   Verified that stage variables (`envAlias` set to `dev` or `prod`) were properly defined under the target stage configuration.

-   Explicitly triggered a redeployment of the API Gateway to the active stage via the AWS Console.

2\. CORS Failures & Preflight `401 Unauthorized` Loops
------------------------------------------------------

### Symptom

The local React frontend became trapped in an endless retry/error loop accompanied by browser console errors stating `CORS error` alongside `401` responses on `OPTIONS` preflight requests.

### Root Cause

Browsers automatically send an `OPTIONS` preflight request *before* executing cross-origin `GET` or `POST` requests. Crucially, **browsers do not attach Authorization headers to preflight requests**.

Because the `OPTIONS` methods on API Gateway routes had the Cognito Authorizer attached, API Gateway rejected every preflight request with a `401 Unauthorized`. This caused the browser to block the subsequent actual request, throwing a CORS error.

### Resolution

1.  Navigated to the `OPTIONS` method for every route (`/summarize`, `/jobs/{job_id}`, `/history`) in API Gateway.

2.  Changed the **Authorization** setting from the Cognito Authorizer to **`NONE`**.

3.  Redeployed the API Gateway stage.

3\. DynamoDB IAM Permission Failures (`Access Denied`)
------------------------------------------------------

### Symptom

Lambda execution logs revealed unhandled exceptions when interacting with DynamoDB, such as:

Plaintext

```
User: arn:aws:sts::321043732559:assumed-role/get-summarization-job-role-... is not authorized to perform: dynamodb:GetItem on resource: arn:aws:dynamodb:ap-southeast-2:321043732559:table/summarization-jobs

```

### Root Cause

The IAM execution roles attached to individual Lambda functions (`get-summarization-job`, `summarization-job-producer`, and the SQS worker) lacked the necessary identity-based permissions to read from or write to the specific DynamoDB tables (`summarization-jobs`, `youtube-summaries`, and `user-submissions`).

### Resolution

Created and attached inline IAM policies to the corresponding Lambda execution roles granting precise permissions:

-   **For `get-summarization-job`:** Allowed `dynamodb:GetItem` on `summarization-jobs`.

-   **For `summarization-job-producer`:** Allowed `dynamodb:PutItem` on `summarization-jobs` and `sqs:SendMessage` on the queue.

-   **For `youtube-summarizer` worker:** Allowed DynamoDB read/write access and S3 `PutObject` permissions.

4\. Lambda Invoke Permissions for API Gateway (`500 Internal Server Error`)
---------------------------------------------------------------------------

### Symptom

After successfully deploying the API to the `prod` stage, calling `POST /summarize` immediately threw an HTTP `500 Internal Server Error`.

### Root Cause

API Gateway lacked explicit permission to invoke the specific production alias (`prod`) of the `summarization-job-producer` Lambda function. While the development stage had permissions wired up, production aliases require explicit qualifier permissions.

### Resolution

Granted API Gateway permission to invoke the production Lambda alias using the AWS CLI:

Bash

```
aws lambda add-permission\
  --function-name summarization-job-producer\
  --qualifier prod\
  --statement-id apigateway-prod-invoke-producer\
  --action lambda:InvokeFunction\
  --principal apigateway.amazonaws.com\
  --source-arn "arn:aws:execute-api:ap-southeast-2:321043732559:etx5b18bqf/*/POST/summarize"

```

5\. Asynchronous Polling Loops (Jobs Stuck in `PENDING` or `PROCESSING`)
------------------------------------------------------------------------

### Symptom

The frontend successfully submitted a job and entered its polling loop (`GET /jobs/{job_id}`), but remained stuck indefinitely because the job status never transitioned to `COMPLETED` or `FAILED`.

### Root Cause

1.  **SQS Worker Failures:** The background worker (`youtube-summarizer`) failed silently due to missing environment variables or unconfigured SSM Parameter Store permissions required to fetch the OpenAI API key.

2.  **Polling Endpoint Errors:** The `get-summarization-job` function lacked permissions or environment mapping in the `prod` environment, causing it to return empty responses or errors that the frontend interpreted as "still loading."

### Resolution

-   Inspected CloudWatch logs for the `youtube-summarizer` SQS worker to trace transcript and OpenAI API exceptions.

-   Ensured production environment variables and IAM policies matched across all three asynchronous microservices (`producer`, `worker`, and `get-job`).