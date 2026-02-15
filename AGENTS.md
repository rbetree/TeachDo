# Repository Guidelines

## 除非用户指定其他语言，否则都以中文回复用户

## Project Structure & Module Organization
- `backend/` FastAPI services: `main_api/` (HTTP API), `slide_agent/` (content), `simpleOutline/` (outline), `personaldb/` (KB), `mock_api/` (demo). Tests live in `backend/test_*.py`.
- `frontend/` Vue 3 + Vite + TS app (`src/`, `public/`).
- `scripts/` utility shell scripts; `doc/` official documentation; `notes/` local notes (gitignored); `template/` static PPT templates; `var/` runtime cache/tmp (gitignored); `logs/` runtime logs (gitignored).

## Build, Test, and Development Commands
- One‑click local stack: `cp env_template.txt .env && python start.py` (installs deps, boots all services, tails logs).
- Backend (all services): `cd backend && pip install -r requirements.txt && python start_backend.py`.
- Backend (single service): `cd backend/main_api && cp env_template .env && uvicorn main:app --reload --port 6800`.
- Frontend: `cd frontend && npm i && npm run dev` (dev) | `npm run build` (prod) | `npm run lint` (eslint).
- Docker: `docker compose up` from repo root.
- Tests: `pytest backend -q` (some streaming tests expect running services; use `mock_api` or start services first).

## Coding Style & Naming Conventions
- Python: PEP 8, 4‑space indent, type hints preferred. Modules and functions `snake_case`; classes `PascalCase`. Test files `test_*.py` next to code or in `backend/`.
- Vue/TS: 2‑space indent, ESLint config in `frontend/.eslintrc.cjs`. Components `PascalCase` files (e.g., `App.vue`), composables `useXxx.ts` in `src/hooks`, Pinia stores in `src/store/*.ts`. Keep API clients under `src/services`.
- Styling: Prefer CSS variables used by the editor (e.g., `--editor-theme-color`). Run `npm run lint` before commits.

## Testing Guidelines
- Frameworks: Python `pytest` + `unittest.IsolatedAsyncioTestCase` for async HTTP checks; front‑end sanity via Vite dev server.
- Conventions: name tests `test_<unit>.py`; focus on API contracts (`/tools/aippt*`, `/templates`, `/data/*`).
- Running: start `main_api`, `simpleOutline`, and `slide_agent` or use `backend/mock_api` when tests depend on streaming endpoints.

## Commit & Pull Request Guidelines
- Commits: Conventional Commits enforced via commitlint (e.g., `feat(frontend): add outline editor` or `fix(backend): keep-alive for SSE`).
- PRs: include a clear summary, linked issues, steps to reproduce/verify, and screenshots for UI changes. Update docs when changing APIs, env vars, or ports.

## Security & Configuration Tips
- Copy `env_template.txt` to `.env` and never commit secrets. Key vars include `HOST`, `MAIN_API_PORT`, `OUTLINE_API_PORT`, `CONTENT_API_PORT`, `PERSONAL_DB`.
- Default ports: backend `6800/10001/10011`, frontend `5173`. Adjust via `.env`.
