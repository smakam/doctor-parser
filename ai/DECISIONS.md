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

## 2026-03-21 — Render Deployment Lessons

**Context**: First deployment to Render free tier (static site for frontend, web service for backend).

**Problems encountered and fixes:**

1. **Vite env vars must be set before build, not after**
   Vite bakes `VITE_*` variables into the JS bundle at build time. Setting them in Render after the first deploy requires a manual redeploy. Missing vars cause a blank page with a cryptic JS error (`supabaseUrl is required`).
   → *Checklist: set all `VITE_*` env vars before the first deploy.*

2. **Render static site rewrites do redirects, not rewrites**
   Adding `/* → /index.html` via the Render UI caused a 302 redirect that stripped the `#access_token` hash fragment from the OAuth callback URL, breaking login.
   → *Fix: change `redirectTo` in `signInWithOAuth` to `window.location.origin` (root) instead of a subpath. The root always serves `index.html` without needing a rewrite rule.*

3. **Supabase uses ES256 (ECDSA), not RS256**
   Newer Supabase projects sign JWTs with ES256, not RS256. Backend was silently swallowing the `alg not allowed` error, returning 401 with no useful log output.
   → *Fix: use `algorithms=["RS256", "ES256"]` in jwt.decode. Add logging to JWT failures immediately — never swallow auth errors silently.*

4. **Guest session lost after OAuth redirect**
   `sessionStorage` is cleared by cross-origin redirects in some scenarios. After OAuth login, the guest session was gone, leaving no auth identity for the accept/correct calls.
   → *Fix: always send both `Authorization` and `X-Guest-Session` headers. Backend falls back to guest session if JWT fails.*

**Deployment checklist for future projects:**
- Set all `VITE_*` frontend env vars before first build
- Set `CORS_ORIGINS` on backend to the exact frontend URL
- Use `redirectTo: window.location.origin` for OAuth on static hosts
- Add Render URL to both Supabase Redirect URLs and Google OAuth authorized origins/redirects
- Use `algorithms=["RS256", "ES256"]` for Supabase JWT verification
- Log JWT failures — never silently swallow auth errors

---

## 2026-03-21 — Geocoding: Mappls → Google Maps

**Context**: Mappls (MapmyIndia) was chosen for Indian address geocoding. All app types (web, cloud, mobile) consistently returned `invalid_token` despite the Geocoding API showing as active in the console.

**Decision**: Switch to Google Maps Geocoding API using the same GCP key already used for Google Vision.

**Reasoning**: No new credentials needed. Google Maps Geocoding works reliably for Indian addresses including pin codes. Mappls may require additional account-level approval that wasn't granted.

**Impact**: `GOOGLE_VISION_API_KEY` now serves double duty for Vision OCR and geocoding. `MAPPLS_API_KEY` is retained in config for backwards compat but unused.

**Related Files**: `backend/app/services/geocoding_service.py`

---

## 2026-07-17 — Native Inline Publication for Action-Based AI Reviews

**Context**: The controlled Codex review experiment found that the hosted
review and repository-owned GitHub Action identified the same defects, but the
Action published one conversation comment instead of resolvable inline review
threads.

**Decision**: Require the Action reviewer to emit structured JSON and publish
it as a native GitHub pull-request review. Attach findings to validated diff
lines and place non-attachable findings in the review summary. Use a hidden
fingerprint scoped to the PR head commit and finding location to suppress
duplicate comments when the same commit is retried.

**Reasoning**: Native review threads match the human review workflow while
preserving the Action's orchestration, model selection, and cost controls.
Commit-scoped fingerprints provide idempotency without hiding findings that
remain after a new commit.

**Impact**:
- The reviewer output is a versioned JSON contract rather than Markdown.
- The publishing job creates one GitHub review with inline comments.
- Humans resolve threads; the automation does not auto-resolve findings.
- A future central reusable workflow can own the publisher implementation.

**Related Files**: `.github/codex/schemas/pr-review.schema.json`,
`.github/codex/scripts/publish-inline-review.cjs`,
`.github/workflows/codex-pr-review.yml`

---

## 2026-07-18 — CI Evidence Report Orchestration

**Context**: The second CI experiment needs to combine deterministic CI tools
with AI interpretation after a pull request is opened. The first review
experiment covered AI code review only; this experiment adds static analysis,
security analysis, backend unit/API tests, CI-time targeted test generation, and
a final reviewer-facing evidence report. Dynamic analysis is intentionally left
for a follow-up because it requires live app startup in CI.

**Decision**: Add a repository-owned GitHub Actions workflow named `CI evidence
report`. Run Ruff, Bandit, and pytest as deterministic evidence producers. Scope
Ruff and Bandit to changed backend Python files initially so baseline findings in
the existing codebase do not drown out PR-specific evidence. Keep static and
security jobs non-blocking at the GitHub job level; preserve their tool exit
codes and changed-file scope in artifacts. Add an always-on deterministic
summary comment so reviewers can see evidence-only Ruff/Bandit findings without
opening artifacts. Add a final readiness gate that fails when blocking evidence
exists, so report publication success is not confused with PR readiness. Keep
backend pytest blocking. Gate
AI-generated targeted tests and the final AI report behind the `ci-ai-report`
label and same-repository PR check. Allow the test-generation step to write only
`ci-generated-tests/backend/test_pr_targeted.py`; fail the job if any other file
is modified. Publish the final AI report as an upserted PR comment using a
stable hidden marker.

**Reasoning**: GitHub Actions is the right orchestration layer for multi-signal
CI because it can run independent tools, preserve artifacts, enforce
permissions, and coordinate a final summarizer. Deterministic tools remain the
source of truth for pass/fail evidence; AI is used to generate small
PR-specific tests and correlate results for a human reviewer. Label-gating keeps
cost and secret exposure under explicit control.

**Impact**:
- Static analysis, security analysis, and backend unit/API tests run on pull
  requests.
- A deterministic PR comment summarizes Ruff, Bandit, and pytest evidence for
  manual reviewers.
- The final `CI readiness gate` check is the machine-readable ready/blocked
  signal for the PR.
- AI-generated tests are temporary CI artifacts, not committed source.
- The final report summarizes tool outputs, generated tests, cross-signal
  interpretation, manual-review focus, and uncertainty.
- OWASP ZAP/dynamic analysis remains out of scope for this PR and should be
  added after test-safe app startup exists in CI.

**Related Files**: `.github/workflows/ci-evidence-report.yml`,
`.github/codex/prompts/targeted-test-generation.md`,
`.github/codex/prompts/ci-final-report.md`

---
