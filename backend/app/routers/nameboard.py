"""
NameboardController — all /api/nameboard/* endpoints.
"""
import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_optional, UserContext
from app.config import get_settings
from app.database import get_db
from app.schemas.nameboard import ExtractionResponse, CorrectRequest
from app.services import image_service, ocr_service, extraction_service, geocoding_service, result_service, review_service

router = APIRouter()


@router.post("/nameboard/extract", response_model=ExtractionResponse)
async def extract(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserContext] = Depends(get_current_user_optional),
):
    """
    Upload 1–5 nameboard images, run the full pipeline, and return the extraction result.
    Accessible to authenticated users and guest sessions.
    """
    import uuid as _uuid
    imagekit_session_id = str(_uuid.uuid4())  # used only for ImageKit folder path

    # Step 1 — upload images to ImageKit
    image_results = await image_service.upload_images(files, imagekit_session_id)

    # Step 2 — OCR all images in parallel
    ocr_results = await ocr_service.extract_text_all([r.url for r in image_results])

    # Step 3 — GPT-4o structured extraction
    extraction = await extraction_service.extract_fields(ocr_results)

    # Step 4 — Geocoding
    address_val = extraction.address.value if extraction.address else None
    pin_val = extraction.pin_code.value if extraction.pin_code else None
    geocoding = await geocoding_service.geocode(address_val, pin_val)

    # Step 5 — Assemble and persist
    is_guest = not current_user or current_user.is_guest
    user_id = current_user.id if current_user else None
    record = await result_service.assemble_and_save(
        db=db,
        session_id=imagekit_session_id,
        image_results=image_results,
        ocr_results=ocr_results,
        extraction=extraction,
        geocoding=geocoding,
        user_id=user_id,
        is_guest=is_guest,
    )

    settings = get_settings()
    return result_service.build_response(record, user_id, settings.pii_encryption_key)


@router.get("/nameboard/{extraction_id}", response_model=ExtractionResponse)
async def get_extraction(
    extraction_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserContext] = Depends(get_current_user_optional),
):
    record = await result_service.get_by_id(db, extraction_id)
    if not record:
        raise HTTPException(status_code=404, detail="Extraction not found.")

    user_id = current_user.id if current_user else None
    _check_access(record, user_id)

    settings = get_settings()
    return result_service.build_response(record, user_id, settings.pii_encryption_key)


@router.post("/nameboard/{extraction_id}/accept", response_model=ExtractionResponse)
async def accept_extraction(
    extraction_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserContext] = Depends(get_current_user_optional),
):
    record = await result_service.get_by_id(db, extraction_id)
    if not record:
        raise HTTPException(status_code=404, detail="Extraction not found.")

    user_id = current_user.id if current_user else None
    _check_access(record, user_id)

    record = await review_service.accept(record, db)
    settings = get_settings()
    return result_service.build_response(record, user_id, settings.pii_encryption_key)


@router.post("/nameboard/{extraction_id}/reject", response_model=ExtractionResponse)
async def reject_extraction(
    extraction_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserContext] = Depends(get_current_user_optional),
):
    record = await result_service.get_by_id(db, extraction_id)
    if not record:
        raise HTTPException(status_code=404, detail="Extraction not found.")

    user_id = current_user.id if current_user else None
    _check_access(record, user_id)

    record = await review_service.reject(record, db)
    settings = get_settings()
    return result_service.build_response(record, user_id, settings.pii_encryption_key)


@router.post("/nameboard/{extraction_id}/correct", response_model=ExtractionResponse)
async def correct_extraction(
    extraction_id: str,
    corrections: CorrectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[UserContext] = Depends(get_current_user_optional),
):
    record = await result_service.get_by_id(db, extraction_id)
    if not record:
        raise HTTPException(status_code=404, detail="Extraction not found.")

    user_id = current_user.id if current_user else None
    _check_access(record, user_id)

    record = await review_service.correct(record, corrections, db)
    settings = get_settings()
    return result_service.build_response(record, user_id, settings.pii_encryption_key)


def _check_access(record, requesting_user_id: Optional[str]) -> None:
    """Ensure the requesting user is the uploader of this record."""
    if not requesting_user_id:
        raise HTTPException(status_code=401, detail="Authentication required.")

    uploader = str(record.uploaded_by_customer_id) if record.uploaded_by_customer_id else None
    if uploader != requesting_user_id and record.session_id != requesting_user_id:
        raise HTTPException(status_code=403, detail="Access denied.")
