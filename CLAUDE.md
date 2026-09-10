# Claude Code Project Guidelines: Serverless YouTube Summarizer

## Architecture & Monorepo Overview
- Monorepo containing `/backend` (AWS Lambda Python 3.13) and `/frontend` (Vite + React 18 + TS).
- **Backend Stack:** Python 3.13, Pytest, OpenAI API (`gpt-4o-mini`), `youtube-transcript-api` (v1.0.0+), DynamoDB (`youtube-summaries`), SSM Parameter Store.
- **Frontend Stack:** React 18, TypeScript, Vite, Tailwind CSS v4, `react-markdown`, `react-icons` (`FaYoutube`), `lucide-react`.

## Common Commands

### Frontend (`/frontend`)
- **Dev Server:** `cd frontend && npm run dev`
- **Build:** `cd frontend && npm run build`
- **Deploy Static Site:** `./deploy-frontend.sh`

### Backend (`/backend`)
- **Run Tests:** `cd backend && python -m pytest tests/`
- **Package Lambda Zip:** `cd backend && ./build.sh` (Generates Linux C-extensions `manylinux2014_x86_64`)

## Code Style & Architectural Constraints

### Backend (Python 3.13)
- **Transcript API Syntax:** Always instantiate `YouTubeTranscriptApi()` before calling `.fetch(video_id)` (v1.0.0+ syntax). Do NOT use static `get_transcript()`.
- **Packaging:** Native dependencies (like `pydantic_core`) must be compiled with `--platform manylinux2014_x86_64` for Lambda compatibility (handled via `backend/build.sh`).
- **Proxy Routing:** External YouTube calls must route through residential proxies using `GenericProxyConfig` via `PROXY_URL`.

### Frontend (TypeScript / React)
- **Type Imports:** Always use explicit type imports (e.g., `import type { StatusState } from '../types'`) to satisfy Vite's transpiler constraints.
- **Icons:** Avoid importing `Youtube` from `lucide-react`. Use `FaYoutube` from `react-icons/fa`.
- **Markdown:** Render model outputs with `react-markdown`.

## Documentation Maintenance
- Update `CONTEXT.md` whenever new deployment steps, CORS fixes, or API contracts change.