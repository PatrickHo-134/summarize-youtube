## **Phase 1: Resilience & Edge-Case Error Handling**

-   **Granular Exception Catching:** Refactor the generic `except Exception` in `lambda_function.py` to target specific failures:

    -   *YouTube API:* Handle `VideoUnavailable`, `TranscriptsDisabled`, `NoTranscriptFound`, and proxy/rate-limiting errors (`429`/`503`) explicitly.

    -   *OpenAI API:* Catch `RateLimitError` (429), `APITimeoutError`, and 128k context-length errors to return proper HTTP status codes instead of opaque 400/502 errors.

-   **Retry and Backoff Logic:** Wrap `get_transcript()` and `summarise()` calls in a retry loop with exponential backoff using `urllib3` or `time.sleep()` to handle transient network drops and proxy blocks.

**Phase 2: Architecture & Scalability**

-   **Asynchronous Status Polling Pattern:** Decouple long-running tasks to bypass API Gateway's 29-second timeout:

    -   Have Lambda check DynamoDB for the video ID on request; if missing, write an item with status `PROCESSING` and return `202 Accepted`.

    -   Offload transcript fetching and summarization asynchronously (via SQS/background invocation).

    -   Update frontend `app.js` to poll a `/status` endpoint until completion.

-   **Data Persistence & Cleanup:**

    -   Separate storage logic to save fetched raw transcripts independently from finalized summaries in DynamoDB.

    -   Configure a DynamoDB Time-To-Live (TTL) attribute (e.g., 90 days) to purge stale cached items.

-   **Configuration Cleanup:** Replace hardcoded API endpoints and infrastructure IDs scattered throughout the source code with dynamic environment variables.

**Phase 3: User Experience, Security & Features**

-   **Authentication & Session Management:** Implement a proper logout button and session invalidation after a designated inactivity window.

-   **User History & Delivery:**

    -   Build the User's History page to display past summaries.

    -   Implement native backend email delivery using AWS SES to allow users to receive formatted HTML summaries.

-   **Abuse Prevention & Cost Control:** Add AWS WAF rules, API Gateway Usage Plans, or Cloudflare Turnstile to `UrlForm.tsx` to stop automated bot scraping and protect OpenAI/proxy budgets.

-   **Model Flexibility:** Migrate away from hardcoded OpenAI endpoints by introducing support for self-hosted LLM models or Amazon Bedrock.

## **Phase 4: DevOps, Testing & Polish**

-   **CI/CD Automation:** Implement GitHub Actions workflows to automate building and deploying frontend and backend updates on pushes to `main` (replacing manual script execution).

-   **Testing & Latency:**

    -   Update and expand unit tests for the Lambda function.

    -   Audit frontend-to-backend communication to optimize request latency.

-   **Infrastructure as Code (IaC):** Convert manual AWS console setups into AWS CDK, SAM, or Terraform templates for reproducible environments, and clean up unneeded resources like CloudFront if redundant.

## Quick note:

## Order of future work

| Rank | Task Category / Item | Importance | Dev Time | Strategic Rationale | Status |
| --- | --- | --- | --- | --- | --- |
| **1** | **Edge-Case Handling & Proxy Rotation** | High | Medium | Catches YouTube/OpenAI exceptions and implements proxy pool rotation to prevent scraping blocks at scale. | DONE |
| **2** | **Replace Hardcoded IDs & Configurations** | High | Low | Removes hardcoded environment values in source code for multi-environment safety. | DONE |
| **3** | **Asynchronous SQS Queuing & Status Polling** | High | High | Decouples long-running jobs via SQS and DynamoDB status tracking to bypass the 29-second API Gateway timeout. |
| **4** | **Request Deduplication Locks & Caching** | High | Medium | Implements DynamoDB conditional writes to prevent duplicate concurrent scrapes and sets up TTL caching. |
| **5** | **Unit Testing & Mock Isolation (pytest/moto)** | High | Medium | Establishes foundational test coverage using mocks to isolate expensive external APIs. | DONE |
| **6** | **Authentication & Session Invalidation** | High | Medium | Introduces proper logout buttons and session expiration to secure user state. | DONE |
| **7** | **Rate Limiting & LLM Token Backpressure** | High | Medium | Protects OpenAI/Bedrock limits and proxy budgets with backoff algorithms and bot protection. |
| **8** | **Fixture-Based Contract Testing (VCR.py)** | Medium-High | Medium | Uses recorded JSON response snapshots to catch upstream YouTube parser breakages early. |
| **9** | **GitHub Actions CI/CD Pipeline** | Medium-High | Medium | Replaces manual scripts with automated builds and test gates on push to `main`. |
| **10** | **UI Component Design Consistency & Polish** | Medium-High | Medium | Standardizes design tokens, component styling, and layout patterns across frontend views for a cohesive UX. | DONE |
| **11** | **User's History Page** | Medium | Medium | Implements the primary user-facing interface to view past generated summaries. | DONE |
| **12** | **AWS SES Email Delivery** | Medium | Low | Moves email distribution from client-side `mailto:` links to a secure backend integration. |
| **13** | **Load Testing (k6/Locust) & LocalStack** | Medium | High | Validates system behavior under high concurrency and emulates AWS services locally. |
| **14** | **Lambda Concurrency & Reserved Limits** | Medium | Low | Sets explicit concurrency boundaries to protect AWS account limits during traffic spikes. |
| **15** | **LLM Migration (Bedrock / Self-Hosted)** | Medium | High | Transitions architecture from OpenAI to flexible or self-hosted model backends. |
| **16** | **Lambda Unit Tests & Latency Tuning** | Medium | Medium | Expands test coverage and optimizes frontend-to-backend payload round-trips. |
| **17** | **Remove CloudFront** | Low | Low | Cleans up redundant networking components to reduce infrastructure overhead. |


