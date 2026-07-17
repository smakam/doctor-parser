# AGENTS.md — Doctor Nameboard Extractor

---

## 🔒 STABLE CONTRACT (Human-Owned — Do Not Auto-Modify)

### Coding Conventions

| Concern | Choice |
|---------|--------|
| Language | Python 3.12 (backend), TypeScript (frontend) |
| Formatter | `ruff format` (backend), `prettier` (frontend) |
| Linter | `ruff` (backend), `eslint` (frontend) |
| Type checker | `mypy` (backend), `tsc` (frontend) |
| Test framework | `pytest` (backend), `vitest` (frontend) |
| Package manager | `uv` or `pip` (backend), `npm` (frontend) |

### Workflow Contract

**Before changes:**
- For any multi-step task, create a plan in `ai/PLAN.md` before writing code
- Read `ai/DECISIONS.md` before touching architecture, service boundaries, or data model

**During changes:**
- Minimal diffs — only change what is necessary for the task
- Match existing code style and naming conventions
- No unrequested refactoring
- No new dependencies without flagging to the user first

**After changes:**
- Run backend tests: `pytest`
- Run backend linting: `ruff check . && ruff format --check .`
- Run frontend linting: `npm run lint`
- Update `ai/STATUS.md` with what was done and what's next

**Before architectural changes:**
- STOP — read `ai/DECISIONS.md`
- Propose the change and rationale, wait for explicit approval
- Record the decision in `ai/DECISIONS.md` after approval

### Pull Request Review Contract

- For every pull-request review, read and follow
  `.github/review/code-review.md`.
- That file is the shared, provider-neutral source of truth for review
  priorities, finding thresholds, severity, validation, and reporting.
- Keep execution-specific instructions in the invoking integration rather than
  duplicating the shared review policy.

### Security Guardrails

- Never hardcode secrets, API keys, or credentials in source code
- Never commit `.env` files — only `.env.example` with placeholder values
- Never log PII (phone numbers, emails) — mask in all log output
- `pii_data` field must always be encrypted at rest and access-gated to uploader
- No destructive database operations (DROP, TRUNCATE) without explicit user approval
- Google OAuth tokens must never be stored in localStorage — use httpOnly cookies or Supabase session management

### Danger Zones

- **`pii_data` column** — access-gated; only return to the uploading user/session. Any change to this logic needs explicit review.
- **Confidence scoring logic** — in `NameboardResultService`. Changes affect downstream quote form population accuracy.
- **GPT-4o prompt** — in `NameboardExtractionService`. Changes to the prompt affect all extraction quality. Test thoroughly before changing.
- **Alembic migrations** — never edit a migration that has already been applied to any environment. Always create a new migration.

---

## 🗺️ REPO MAP (Update only on structural changes — propose diff first)

**Purpose**: AI-powered extraction of structured doctor information from nameboard/visiting card photos, for populating Professional Indemnity insurance quote forms.

### Directory Structure

```
doctor-parser/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Settings via pydantic-settings
│   │   ├── database.py          # SQLAlchemy async engine + session
│   │   ├── models/
│   │   │   └── nameboard.py     # SQLAlchemy ORM model (nameboard_extractions table)
│   │   ├── routers/
│   │   │   └── nameboard.py     # NameboardController — all /api/nameboard/* routes
│   │   └── services/
│   │       ├── image_service.py       # NameboardImageService — ImageKit upload
│   │       ├── ocr_service.py         # NameboardOcrService — Google Vision
│   │       ├── extraction_service.py  # NameboardExtractionService — GPT-4o
│   │       ├── geocoding_service.py   # NameboardGeocodingService — Mappls
│   │       └── result_service.py      # NameboardResultService — assemble + persist
│   ├── tests/
│   ├── alembic/                 # DB migrations
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/          # shadcn/ui + custom components
│   │   ├── pages/               # Upload, Processing, Review, QuoteForm
│   │   ├── lib/                 # API client, utils
│   │   └── main.tsx
│   ├── package.json
│   └── .env.example
├── docs/
│   └── PROJECT_BRIEF.md
├── ai/
│   ├── PLAN.md       (gitignored — ephemeral)
│   ├── STATUS.md     (gitignored — ephemeral)
│   └── DECISIONS.md  (committed — permanent record)
├── AGENTS.md
├── CLAUDE.md
└── README.md
```

### Entry Points

- Backend: `backend/app/main.py` — `uvicorn app.main:app`
- Frontend: `frontend/src/main.tsx` — `npm run dev`

### Key Commands

```bash
# Backend
cd backend
pip install -r requirements.txt   # install deps
uvicorn app.main:app --reload     # start dev server (port 8000)
pytest                            # run tests
ruff check . && ruff format .     # lint + format
alembic upgrade head              # apply migrations

# Frontend
cd frontend
npm install                       # install deps
npm run dev                       # start dev server (port 5173)
npm run build                     # production build
npm run lint                      # lint
```

---

## ✅ TASK MANAGEMENT

- Use `ai/PLAN.md` for the current task list and implementation plan
- Use `ai/STATUS.md` to track progress, blockers, and files touched
- Use `ai/DECISIONS.md` to record every significant architectural decision

### .gitignore rules for ai/

```
ai/PLAN.md      # ephemeral — not committed
ai/STATUS.md    # ephemeral — not committed
# ai/DECISIONS.md is committed
```
