# Claude Code Project Guidelines: Serverless YouTube Summarizer

## Architecture & Monorepo Overview
- Monorepo containing `/backend` (AWS Lambda Python 3.13) and `/frontend` (Vite + React 18 + TS).
- **Backend Stack:** Python 3.13, Pytest, OpenAI API (`gpt-4o-mini`), `youtube-transcript-api` (v1.0.0+), DynamoDB (`youtube-summaries`), Amazon S3 (raw transcript cache), SSM Parameter Store.
- **Frontend Stack:** React 18, TypeScript, Vite, Tailwind CSS v4, `react-markdown`, `react-icons` (`FaYoutube`), `lucide-react`.

## Common Commands

### Frontend (`/frontend`)
- **Dev Server:** `cd frontend && npm run dev`
- **Build:** `cd frontend && npm run build`
- **Deploy Static Site:** `./deploy-frontend.sh`

### Backend (`/backend`)
- **Run Tests (summarize):** `backend/venv/bin/python -m pytest backend/summarize/tests/test_lambda_function.py -v`
- **Run Tests (get_history):** `backend/venv/bin/python -m pytest backend/get_history/tests/test_lambda_function.py -v`
- **First-time venv setup:** `python3.13 -m venv backend/venv && backend/venv/bin/pip install -r backend/summarize/requirements-dev.txt`
- **Package summarize Lambda Zip:** `cd backend/summarize && ./build.sh` (Generates Linux C-extensions `manylinux2014_x86_64`)
- **Package get_history Lambda Zip:** `cd backend/get_history && ./build.sh`

## Code Style & Architectural Constraints

### Backend (Python 3.13)
- **Transcript API Syntax:** Always instantiate `YouTubeTranscriptApi()` before calling `.fetch(video_id)` (v1.0.0+ syntax). Do NOT use static `get_transcript()`.
- **Packaging:** Native dependencies (like `pydantic_core`) must be compiled with `--platform manylinux2014_x86_64` for Lambda compatibility (handled via `backend/summarize/build.sh`). `backend/get_history/build.sh` requires no cross-compilation (pure-Python).
- **Proxy Routing:** External YouTube calls must route through residential proxies using `GenericProxyConfig` via `PROXY_URL`.
- **Storage Constraints:** DynamoDB enforces a strict 400KB item limit. Raw transcripts must be stored in S3 (`TRANSCRIPT_BUCKET`) using a non-blocking, fire-and-forget upload pattern to prevent blocking the user if the S3 upload fails. DynamoDB is reserved for caching the shorter generated summaries.

### Frontend (TypeScript / React)
- **Type Imports:** Always use explicit type imports (e.g., `import type { StatusState } from '../types'`) to satisfy Vite's transpiler constraints.
- **Icons:** Avoid importing `Youtube` from `lucide-react`. Use `FaYoutube` from `react-icons/fa`.
- **Markdown:** Render model outputs with `react-markdown`.

## Documentation Maintenance
- Update `CONTEXT.md` whenever new deployment steps, CORS fixes, or API contracts change.