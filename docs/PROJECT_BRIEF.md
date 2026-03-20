# Project Brief: Doctor Nameboard Extractor

> **Status**: Approved
> **Last Updated**: 2026-03-20

---

## Overview

**Product Name**: Doctor Nameboard Extractor
**Tagline**: Extract structured doctor profile data from nameboard/visiting card photos using AI — instantly ready for insurance quote form population.
**Problem**: Manually entering doctor details (name, qualifications, registration number, address) into Professional Indemnity insurance quote forms is slow and error-prone. This tool lets users photograph a doctor's nameboard and auto-populate those fields with AI-extracted, user-reviewed data.
**Target Users**: Insurance POSP agents and customers filling out Professional Indemnity quotes for doctors in India.

---

## MVP Feature List

1. **Multi-Image Upload** — Accept 1–5 JPEG/PNG images (max 10MB each), upload to ImageKit under a session-scoped path (`/nameboards/{sessionId}/{index}/`). Supports both authenticated (Google OAuth) and guest sessions.

2. **OCR Extraction** — Run Google Cloud Vision Document Text Detection on each image. Returns raw text blocks with bounding boxes, per-word confidence scores, and detected languages per image. Images with average confidence < 0.5 flagged as POOR quality.

3. **AI Structured Extraction** — Send OCR output to GPT-4o (JSON mode) with an India-specific medical prompt to extract: `doctorName`, `clinicName`, `specialisation`, `qualifications`, `medicalRegistrationNo`, `address`, `pinCode`, `consultationTimings` — each with a `confidence` score (0.0–1.0). Cross-image confidence boost applied when the same value appears in 2+ images (×1.15, capped at 1.0).

4. **Geocoding** — Use Mappls tiered strategy to derive lat/long, city, and state:
   - Full address + pinCode → Mappls address geocode
   - pinCode only → Mappls pin code centroid
   - Address only → Mappls geocode (lower confidence)
   - Neither → NOT_GEOCODED

5. **Review Screen** — Display extracted fields as editable inputs with colour-coded confidence indicators (green ≥ 0.85, amber 0.70–0.85, red < 0.70). Show uploaded images alongside. Surface image quality warnings inline.

6. **Accept / Correct / Reject** — User confirms, edits, or rejects the extraction. Corrections preserve original extracted values for audit. Accepted/corrected data maps into the quote form fields.

7. **PII Handling** — Phone numbers and emails stored encrypted, returned only to the uploader. Guest session PII purged on session expiry.

---

## Out of Scope (v1)

- Regional/Indic script OCR (Tamil, Hindi, etc.) — hooks exist in data model, not activated
- Image pre-processing (contrast enhancement, deskew) — v2 enhancement
- Auto-accept without manual review
- Batch processing across multiple doctors in one session
- Admin dashboard or analytics
- Mobile native app (web responsive only)

---

## Success Metrics

- Extraction completes end-to-end in under 15 seconds for 3 images
- Overall confidence ≥ 0.85 on clear nameboard photos in good lighting
- User can review and populate quote form in under 2 minutes
- Zero PII leakage across users in testing

---

## Tech Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Language | Python 3.12 | |
| Backend Framework | FastAPI | Async, modern, excellent AI API ecosystem |
| Database | PostgreSQL (Supabase) | JSONB columns for extracted data and PII; free tier |
| Auth | Google OAuth via Supabase | Guest token flow also supported |
| Image Storage | ImageKit | CDN + storage for nameboard photos; free tier |
| Frontend | React + Vite | |
| UI Components | shadcn/ui + Tailwind CSS | Production-quality, customizable |
| OCR | Google Cloud Vision API | Document Text Detection; 1,000 free calls/month |
| LLM | OpenAI GPT-4o | JSON mode; ~$0.01–0.05 per extraction |
| Geocoding | Mappls | India-specific; free tier for dev |
| Backend Hosting | Render | Free tier (note: spins down after inactivity) |
| Frontend Hosting | Vercel | Free tier |
| DB Migrations | Alembic | Standard FastAPI/SQLAlchemy migration tool |

---

## API Endpoints

```
POST   /api/nameboard/extract              — upload images, run full pipeline
GET    /api/nameboard/{extractionId}       — retrieve a previous extraction
POST   /api/nameboard/{extractionId}/accept
POST   /api/nameboard/{extractionId}/reject
POST   /api/nameboard/{extractionId}/correct
```

## Pipeline Order

```
1. NameboardImageService.upload(images)           → ImageKit URLs + fileIds
2. NameboardOcrService.extractText(urls)          → raw text blocks + quality scores  [parallelisable per-image]
3. NameboardExtractionService.extractFields(text) → structured fields + confidences
4. NameboardGeocodingService.geocode(fields)      → lat/long + city/state
5. NameboardResultService.assemble(...)           → final response + DB persist
```

---

## Open Questions

- [ ] What is the guest session token format/lifetime? (to match existing quote flow if integrated later)
- [ ] Mappls — do we need to register for a specific API tier for geocoding?
- [ ] Is there a target response time SLA beyond the 15-second guideline?
- [ ] Will this service eventually be embedded into a larger platform, or remain standalone?

---

## Notes

- Confidence scoring: weighted average of per-field confidences (doctorName and address weighted higher). Multiplied down if any image is POOR quality.
- Conflicting values across images: use value from higher text-density image, reduce confidence.
- `pii_data` column encrypted at rest; returned in API response only to the uploader (same customer or POSP).
- Originally requested in Spring Boot/Java — switched to FastAPI/Python for faster development velocity and better AI API ecosystem support.
