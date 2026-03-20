# Architecture & Design Decisions

This file records significant technical decisions for future reference.
Keep entries dated and honest — document the reasoning, not just the outcome.

---

## 2026-03-20 — Tech Stack Selection

**Context**: Greenfield standalone service for doctor nameboard extraction. Original request was Spring Boot/Java + React. Developer is not familiar with Java/Spring Boot.

**Decision**: FastAPI (Python 3.12) + React (Vite + shadcn/ui + Tailwind) + PostgreSQL (Supabase) + Vercel/Render hosting.

**Alternatives Considered**:
- **Spring Boot / Java**: Originally requested, but developer is unfamiliar with it. Steeper learning curve would significantly slow MVP development. Java also has a weaker ecosystem for AI API integrations (GPT-4o, Google Vision).
- **NestJS / TypeScript**: Good option — shares TypeScript with frontend. Rejected in favour of Python because Python has better libraries for AI/ML API integrations and faster iteration for this type of service.
- **Streamlit / Gradio**: Considered for frontend. Rejected — too limited for the required multi-step UX (image upload with camera, colour-coded confidence fields, side-by-side review layout).

**Reasoning**: FastAPI gives async performance with excellent developer ergonomics and the best ecosystem for OpenAI + Google Vision integrations. Supabase provides free PostgreSQL + built-in Google OAuth, reducing setup overhead. shadcn/ui + Tailwind gives production-quality UI without custom design work. Vercel + Render are free-tier friendly for MVP.

**Impact**:
- All backend code in Python 3.12
- FastAPI patterns used throughout (routers, Depends for dependency injection, Pydantic for validation)
- Database schema managed via Alembic migrations
- Frontend in TypeScript with React 18 + Vite build tooling

**Related Files**: AGENTS.md, docs/PROJECT_BRIEF.md

---

## 2026-03-20 — Auth Strategy

**Context**: Service needs to support both logged-in users (Google OAuth) and guest sessions (for pre-login quote flows).

**Decision**: Use Supabase Auth with Google OAuth provider. Guest sessions use a short-lived anonymous token issued by the backend.

**Reasoning**: Supabase Auth is already included with the Supabase free tier (no extra cost). It handles Google OAuth token management, refresh, and session storage securely. Building custom OAuth from scratch would add significant complexity for no benefit at MVP stage.

**Impact**:
- Frontend uses Supabase JS client for auth
- Backend validates Supabase JWTs on protected endpoints
- `uploaded_by_customer_id` on `nameboard_extractions` is nullable to support guest flow

**Related Files**: AGENTS.md, docs/PROJECT_BRIEF.md

---

[Future decisions follow the same format]
