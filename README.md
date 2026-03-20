# Doctor Nameboard Extractor

Extract structured doctor profile data from nameboard/visiting card photos using AI — instantly ready for insurance quote form population.

## Overview

Upload 1–5 photos of a doctor's nameboard. The service runs OCR (Google Vision) and AI extraction (GPT-4o) to pull out the doctor's name, qualifications, registration number, address, and more. Review the extracted data with confidence indicators, make corrections, and populate your quote form in seconds.

## Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- A Supabase project (free tier)
- API keys — see `.env.example` files

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in your credentials
alembic upgrade head   # run DB migrations
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # fill in your Supabase + API URL
npm run dev
```

Frontend runs at `http://localhost:5173`

## Development

```bash
# Backend tests
cd backend && pytest

# Backend linting
cd backend && ruff check . && ruff format .

# Frontend linting
cd frontend && npm run lint
```

## See Also

- [Project Brief](docs/PROJECT_BRIEF.md) — PRD and MVP scope
- [Architecture Decisions](ai/DECISIONS.md) — technical decision log
- [AGENTS.md](AGENTS.md) — coding conventions and workflow rules
