# Claude Code Project Guidelines: Serverless YouTube Summarizer

## Architecture & Monorepo Overview
- Monorepo containing `/backend` (AWS Lambda Python 3.13) and `/frontend` (Vite + React 18 + TS).
- **Async Job-Queue Architecture:** `POST /summarize` is handled by the `producer` Lambda, which checks the `youtube-summaries` cache; on a miss it writes a `PENDING` record to `summarization-jobs` (DynamoDB) and enqueues a message to SQS. The `summarize` Lambda (SQS worker) consumes the queue, transitions the job `PROCESSING` → `COMPLETED`/`FAILED`, and writes the result. The frontend polls `GET /jobs/{job_id}`, served by the `job_status` Lambda, until the job reaches a terminal state.
- **Backend Stack:** Python 3.13, Pytest, OpenAI API (`gpt-4o-mini`), `youtube-transcript-api` (v1.0.0+), DynamoDB (`youtube-summaries`, `summarization-jobs`), Amazon SQS (`SQS_QUEUE_URL`), Amazon S3 (raw transcript cache), SSM Parameter Store.
- **Backend Services:** `producer` (`POST /summarize`), `summarize` (SQS worker), `job_status` (`GET /jobs/{job_id}`), `get_history` (`GET /history`).
- **Frontend Stack:** React 18, TypeScript, Vite, Tailwind CSS v4, `react-markdown`, `react-icons` (`FaYoutube`), `lucide-react`.

## Common Commands

### Frontend (`/frontend`)
- **Dev Server:** `cd frontend && npm run dev`
- **Build:** `cd frontend && npm run build`
- **Deploy Static Site:** `./deploy-frontend.sh`

### Backend (`/backend`)
- **Run Tests (summarize):** `backend/venv/bin/python -m pytest backend/summarize/tests/test_lambda_function.py -v`
- **Run Tests (get_history):** `backend/venv/bin/python -m pytest backend/get_history/tests/test_lambda_function.py -v`
- **Run Tests (producer):** `backend/venv/bin/python -m pytest backend/producer/tests/test_lambda_function.py -v`
- **Run Tests (job_status):** `backend/venv/bin/python -m pytest backend/job_status/tests/test_lambda_function.py -v`
- **Note:** Run each service's test suite individually (not combined in one `pytest` invocation). Packages share the `tests.test_lambda_function` module path with no top-level `__init__.py`, causing collisions when collected together.
- **First-time venv setup:** `python3.13 -m venv backend/venv && backend/venv/bin/pip install -r backend/summarize/requirements-dev.txt`
- **Package summarize Lambda Zip:** `cd backend/summarize && ./build.sh` (Generates Linux C-extensions `manylinux2014_x86_64`)
- **Package get_history Lambda Zip:** `cd backend/get_history && ./build.sh`
- **Package producer Lambda Zip:** `cd backend/producer && ./build.sh` (pure-Python, no cross-compilation)
- **Package job_status Lambda Zip:** `cd backend/job_status && ./build.sh` (pure-Python, no cross-compilation)

## Code Style & Architectural Constraints

### Backend (Python 3.13)
- **Transcript API Syntax:** Always instantiate `YouTubeTranscriptApi()` before calling `.fetch(video_id)` (v1.0.0+ syntax). Do NOT use static `get_transcript()`.
- **Packaging:** Native dependencies (like `pydantic_core`) must be compiled with `--platform manylinux2014_x86_64` for Lambda compatibility (handled via `backend/summarize/build.sh`). `backend/get_history/build.sh`, `backend/producer/build.sh`, and `backend/job_status/build.sh` require no cross-compilation (pure-Python).
- **Proxy Routing:** External YouTube calls must route through residential proxies using `GenericProxyConfig` via `PROXY_URL`.
- **Storage Constraints:** DynamoDB enforces a strict 400KB item limit. Raw transcripts must be stored in S3 (`TRANSCRIPT_BUCKET`) using a non-blocking, fire-and-forget upload pattern to prevent blocking the user if the S3 upload fails. DynamoDB is reserved for caching the shorter generated summaries.
- **Config Module Pattern:** Each service defines `src/config.py` exposing env vars via `_require(name)` (raises `RuntimeError` if unset) and `_optional(name, default)` helpers. `CORS_HEADERS` lives in `config.py` for `producer` and `job_status` rather than being inlined in `lambda_function.py`.
- **Handler Entry Point:** All backend Lambdas expose `lambda_handler` as the entry point name (standardize new services on this; do not use bare `handler`).
- **Job Ownership Checks:** `job_status` must verify `job['user_id'] == user_id` from the Cognito `sub` claim and return `403 Forbidden` on mismatch, `404 Not Found` if the job doesn't exist.
- **DynamoDB Reserved Words:** `result` is a reserved word in DynamoDB `UpdateExpression`s; alias it via `ExpressionAttributeNames` (e.g., `#res`) when `summarize` writes job results.

### Frontend (TypeScript / React)
- **Type Imports:** Always use explicit type imports (e.g., `import type { StatusState } from '../types'`) to satisfy Vite's transpiler constraints.
- **Icons:** Avoid importing `Youtube` from `lucide-react`. Use `FaYoutube` from `react-icons/fa`.
- **Markdown:** Render model outputs with `react-markdown`.
- **API Client:** All HTTP calls to the backend live in `frontend/src/services/api.ts` (`submitSummarizationJob`, `checkJobStatus`, `extractVideoId`, `ApiRequestError`). `extractVideoId` must stay regex-compatible with the backend's video ID extraction.
- **Async Polling:** `useSummarize.ts` submits a job then polls `GET /jobs/{job_id}` on an interval until `COMPLETED`/`FAILED`. Use refs (not state) for interval IDs and in-flight guards, and always clear the interval in a cleanup `useEffect` on unmount.

## Documentation Maintenance
- Update `CONTEXT.md` whenever new deployment steps, CORS fixes, or API contracts change.