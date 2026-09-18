# Dedicated Lambda for the History / Dashboard Endpoint

## Context

The Dashboard component requires a `GET /history` API to fetch a paginated list of a user's past summaries from the `user-submissions` DynamoDB table. At the time of this decision the backend consists of a single Lambda function (`youtube-summarizer`) that handles `POST /summarize` requests.

Two approaches were evaluated for serving the new endpoint:

**Option A – Route dispatch inside the existing Lambda**
Add a conditional branch inside `lambda_function.py` that inspects `httpMethod` and `path`, delegating to a `history_handler()` when the request is `GET /history`.

**Option B – Dedicated Lambda function**
Create a separate `history-lambda` function with its own API Gateway integration, IAM role, and deployment artifact, leaving the summarize function untouched.

---

## Decision

**Option B — a dedicated `history-lambda` function** was chosen.

---

## Rationale

### 1. The async SQS pattern makes a monolith untenable (Roadmap Rank 3)

The highest-priority upcoming architectural item is decoupling long-running jobs via SQS to bypass API Gateway's 29-second timeout. When implemented, `summarize-lambda` will no longer be a synchronous request-response handler — it will become a lightweight **job dispatcher** that writes a `PROCESSING` record to DynamoDB and returns `202 Accepted` immediately. The actual transcript fetch and summarisation will move to a separate **worker Lambda** triggered by SQS.

At that point the monolith would already need to be broken apart. Routing history through `summarize-lambda` today would mean ripping it out again in the near future. Choosing a dedicated function now avoids that double migration.

### 2. The two operations have fundamentally different resource profiles

| Dimension         | `summarize-lambda`               | `history-lambda`           |
|-------------------|----------------------------------|----------------------------|
| Memory            | 512 MB (OpenAI SDK, proxy libs)  | 128 MB (boto3 only)        |
| Timeout           | 30 s (transcript + LLM latency)  | 10 s (DynamoDB GSI read)   |
| External calls    | YouTube, residential proxy, OpenAI | DynamoDB only            |
| Cold-start weight | Heavy (large dependency bundle)  | Minimal                    |

Running a cheap DynamoDB read inside a 512 MB / 30 s function wastes memory allocation and inflates billing. Separate functions allow each to be right-sized independently.

### 3. Reserved concurrency must be set per function (Roadmap Rank 14)

AWS Lambda reserved concurrency is a function-level setting. The summarize workflow is expensive (proxy egress, OpenAI tokens) and must be throttled tightly to protect budgets. The history endpoint is read-only and can tolerate higher concurrency without cost risk. A monolithic function cannot express both limits simultaneously.

### 4. Independent deployability supports the CI/CD pipeline (Roadmap Rank 9)

When GitHub Actions pipelines are introduced, a bug fix to the history pagination logic should not require rebuilding the `deployment.zip` that contains all of the `youtube-transcript-api` and `openai` native extensions. Separate artifacts allow targeted, faster deploys with smaller blast radius.

### 5. IaC models functions as first-class constructs (Roadmap Phase 4)

AWS CDK, SAM, and Terraform all treat Lambda functions as discrete resources. Extracting history into its own function now means the IaC migration later will find the code already organised along the grain of the infrastructure model, rather than having to decompose a monolith as part of the IaC authoring work.

---

## Consequences

### Immediate

- A new `backend/src/history_function.py` is created containing `history_handler()` and `get_user_history()`.
- `backend/src/config.py` (which contains `USER_SUBMISSIONS_TABLE`, `USER_SUBMISSIONS_GSI`, `HISTORY_PAGE_LIMIT`, etc.) is extracted into a **shared Lambda Layer** (`youtube-summarizer-shared`) so both functions consume the same configuration module without copying code.
- A new IAM execution role is created for `history-lambda` with `DynamoDB:Query` on `user-submissions` only — no SSM, no OpenAI, no proxy access.
- A new API Gateway resource `GET /history` is wired to `history-lambda` with the same Cognito User Pool Authorizer.
- `backend/build.sh` gains a second build target producing `history-deployment.zip`.

### Future (when async SQS pattern lands)

The three-function end-state will look like:

```
API Gateway
  ├── POST /summarize  →  summarize-lambda (dispatcher)
  │                           │
  │                           └── SQS Queue  →  worker-lambda
  │
  └── GET  /history   →  history-lambda
```

`summarize-lambda` will shrink further once transcript fetching and LLM calls move into `worker-lambda`, making each function's responsibility — and its dependency bundle — even smaller.

---

## Alternatives Rejected

**Option A (route dispatch inside existing Lambda)** was rejected because:

- It couples the lifecycle of a cheap read operation to an expensive, slow-path function.
- It cannot support different reserved concurrency limits per operation.
- It will need to be undone when the async SQS pattern is implemented, creating unnecessary rework.
- It fights the grain of the planned IaC and CI/CD infrastructure.
