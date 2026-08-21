Core System Architecture
------------------------

### 1\. Frontend Hosting: Amazon S3 + CloudFront (Improvement)

-   **S3 Static Website Hosting:** Perfect for your HTML/JS/CSS files.

-   **Architectural Improvement:** Do not expose the S3 bucket directly to the internet. Put **Amazon CloudFront** (a Content Delivery Network) in front of S3. S3 static hosting does not support HTTPS with custom domains on its own. CloudFront gives you SSL/HTTPS (crucial for security), caches your UI globally for faster loading, and prevents direct access to your bucket.

### 2\. API & Compute: API Gateway + AWS Lambda

-   **Amazon API Gateway (HTTP API):** Acts as the front door, routing frontend requests to your backend logic.

-   **AWS Lambda:** Executes your Python script.

-   **Validation Logic:** Your Lambda function should inspect the incoming request body. If the `youtube_url` is missing or fails a Regular Expression check for valid YouTube formats, Lambda immediately returns a `400 Bad Request` before calling any other services.

### 3\. Secrets Management: AWS SSM Parameter Store

-   **Your Suggestion is Spot On:** AWS Systems Manager (SSM) Parameter Store is the most relevant service here.

-   By storing your OpenAI/LLM API keys as a **SecureString**, it encrypts the data using AWS KMS. It is completely free for standard throughput, making it more cost-effective than AWS Secrets Manager while offering the exact same security for this use case. Your Lambda will fetch this key at runtime.

### 4\. Database (Caching & Deduplication): Amazon DynamoDB

-   **Amazon DynamoDB:** This is the ideal database for this architecture. Its NoSQL design, low latency, and seamless serverless integration make it perfect for rapid key-value lookups.

-   **Schema Design:** Use the extracted YouTube `VideoID` as the **Partition Key**.

-   **The Flow:** When a request hits Lambda, it first queries DynamoDB for the `VideoID`. If a record exists, it immediately returns the stored summary (saving LLM costs and time). If not, it fetches the transcript, calls the LLM, writes the new summary to DynamoDB, and returns the result.

### 5\. Error Handling

-   **External Service Failures:** Wrap your OpenAI API calls in a `try/except` block. If the LLM service times out or returns a 500-level error, catch the exception and return a clean `502 Bad Gateway` to the frontend with a friendly message (e.g., "The AI provider is currently unavailable, please try again later.").

### 6\. Future-Proofing for Authentication: Amazon Cognito

-   **Amazon Cognito User Pools:** When you are ready to launch accounts and logins, Cognito is the native choice.

-   **Integration:** You can attach a Cognito JWT Authorizer directly to your API Gateway route. Once enabled, API Gateway will automatically block any request that doesn't include a valid user token, meaning you won't have to rewrite your Lambda code to implement security.

Critical Architectural Consideration: The 30-Second Limit
---------------------------------------------------------

API Gateway has a hard, unchangeable timeout limit of **30 seconds**. If a YouTube video is extremely long, fetching the transcript and generating a summary via an LLM might take 40 or 50 seconds. In this scenario, API Gateway will drop the connection and return a 504 Timeout to the user, even if Lambda is still running.

**How to address this if it becomes an issue:** You would transition to an asynchronous design. The frontend submits the URL; API Gateway immediately returns a "Job ID" (Status 202). A background service (like SQS or Step Functions) processes the summary and saves it to DynamoDB. The frontend then polls the database every few seconds using that Job ID until the summary appears.