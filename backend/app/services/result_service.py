"""
NameboardResultService — assembles the final extraction result, computes overall
confidence, handles PII encryption, and persists to the database.
"""

import json
import uuid
from typing import Optional

from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.models.nameboard import NameboardExtraction
from app.schemas.nameboard import (
    ExtractionResponse,
    ExtractedData,
    ExtractedField,
    ImageQualityResult,
    PiiData,
)
from app.services.image_service import ImageUploadResult
from app.services.ocr_service import ImageOcrResult
from app.services.extraction_service import ExtractionResult, FieldResult
from app.services.geocoding_service import GeocodingResult

# Weights for overall confidence computation
FIELD_WEIGHTS = {
    "doctor_name": 0.25,
    "address": 0.20,
    "medical_registration_no": 0.15,
    "qualifications": 0.15,
    "specialisation": 0.10,
    "clinic_name": 0.05,
    "pin_code": 0.05,
    "consultation_timings": 0.05,
}


async def assemble_and_save(
    db: AsyncSession,
    session_id: str,
    image_results: list[ImageUploadResult],
    ocr_results: list[ImageOcrResult],
    extraction: ExtractionResult,
    geocoding: GeocodingResult,
    user_id: Optional[str],
    is_guest: bool = False,
) -> NameboardExtraction:
    settings = get_settings()

    extracted_data = _build_extracted_data(extraction, geocoding)
    image_quality = _build_image_quality(ocr_results, image_results)
    extraction_warnings = _build_warnings(ocr_results, extraction)
    overall_confidence = _compute_overall_confidence(extraction, ocr_results)
    pii_encrypted = _encrypt_pii(
        {"phones": extraction.pii_phones, "emails": extraction.pii_emails},
        settings.pii_encryption_key,
    )

    # Store user_id in session_id for access control.
    # For authenticated users, also store in uploaded_by_customer_id.
    # For guests, session_id is the only identifier we have.
    customer_id = None
    if user_id and not is_guest:
        try:
            customer_id = uuid.UUID(user_id)
        except ValueError:
            pass

    record = NameboardExtraction(
        id=uuid.uuid4(),
        session_id=user_id or session_id,  # user_id as access-control key
        uploaded_by_customer_id=customer_id,
        imagekit_file_ids=[r.file_id for r in image_results],
        images_processed=len(ocr_results),
        overall_confidence=overall_confidence,
        extracted_data=extracted_data.model_dump(),
        pii_data={"encrypted": pii_encrypted},
        image_quality=[q.model_dump() for q in image_quality],
        extraction_warnings=extraction_warnings,
        geocoding_status=geocoding.geocoding_status,
        status="PENDING_REVIEW",
    )

    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


def build_response(
    record: NameboardExtraction,
    requesting_user_id: Optional[str],
    pii_encryption_key: str,
) -> ExtractionResponse:
    extracted = ExtractedData(**record.extracted_data)
    image_quality = [ImageQualityResult(**q) for q in (record.image_quality or [])]
    warnings = record.extraction_warnings or []

    pii = None
    uploader_id = (
        str(record.uploaded_by_customer_id) if record.uploaded_by_customer_id else None
    )
    if requesting_user_id and (
        uploader_id == requesting_user_id or record.session_id == requesting_user_id
    ):
        pii = _decrypt_pii(record.pii_data, pii_encryption_key)

    return ExtractionResponse(
        id=str(record.id),
        session_id=record.session_id,
        images_processed=record.images_processed or 0,
        overall_confidence=float(record.overall_confidence or 0),
        extracted_data=extracted,
        image_quality=image_quality,
        extraction_warnings=warnings,
        geocoding_status=record.geocoding_status or "NOT_GEOCODED",
        status=record.status,
        pii_data=pii,
        created_at=record.created_at,
    )


async def list_by_user(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
) -> list[NameboardExtraction]:
    result = await db.execute(
        select(NameboardExtraction)
        .where(
            (NameboardExtraction.session_id == user_id)
            | (NameboardExtraction.uploaded_by_customer_id == _try_uuid(user_id))
        )
        .order_by(NameboardExtraction.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def _try_uuid(value: str):
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


async def get_by_id(
    db: AsyncSession, extraction_id: str
) -> Optional[NameboardExtraction]:
    result = await db.execute(
        select(NameboardExtraction).where(
            NameboardExtraction.id == uuid.UUID(extraction_id)
        )
    )
    return result.scalar_one_or_none()


def _build_extracted_data(
    extraction: ExtractionResult, geocoding: GeocodingResult
) -> ExtractedData:
    def to_schema(field: Optional[FieldResult]) -> Optional[ExtractedField]:
        if field is None:
            return None
        return ExtractedField(value=field.value, confidence=field.confidence)

    return ExtractedData(
        doctor_name=to_schema(extraction.doctor_name),
        clinic_name=to_schema(extraction.clinic_name),
        specialisation=to_schema(extraction.specialisation),
        qualifications=to_schema(extraction.qualifications),
        medical_registration_no=to_schema(extraction.medical_registration_no),
        address=to_schema(extraction.address),
        pin_code=to_schema(extraction.pin_code),
        consultation_timings=to_schema(extraction.consultation_timings),
        latitude=geocoding.latitude,
        longitude=geocoding.longitude,
        city=geocoding.city,
        state=geocoding.state,
    )


def _build_image_quality(
    ocr_results: list[ImageOcrResult],
    image_results: list[ImageUploadResult],
) -> list[ImageQualityResult]:
    output = []
    for ocr in ocr_results:
        warnings = []
        if ocr.quality == "POOR":
            warnings.append(
                "Low OCR confidence — check this image for obstructions or blur."
            )
        if not ocr.raw_text.strip():
            warnings.append("No text detected in this image.")
        output.append(
            ImageQualityResult(
                imagekit_url=ocr.imagekit_url,
                average_word_confidence=ocr.average_word_confidence,
                text_density=ocr.text_density,
                quality=ocr.quality,
                detected_languages=ocr.detected_languages,
                warnings=warnings,
            )
        )
    return output


def _build_warnings(
    ocr_results: list[ImageOcrResult], extraction: ExtractionResult
) -> list[str]:
    warnings = []
    poor_images = sum(1 for o in ocr_results if o.quality == "POOR")
    if poor_images:
        warnings.append(
            f"{poor_images} image(s) had low OCR confidence. Review highlighted fields carefully."
        )
    if not extraction.doctor_name or not extraction.doctor_name.value:
        warnings.append(
            "Doctor name could not be extracted — please enter it manually."
        )
    if not extraction.address or not extraction.address.value:
        warnings.append("Address could not be extracted — please enter it manually.")
    return warnings


def _compute_overall_confidence(
    extraction: ExtractionResult,
    ocr_results: list[ImageOcrResult],
) -> float:
    weighted_sum = 0.0
    weight_total = 0.0

    for attr, weight in FIELD_WEIGHTS.items():
        field: Optional[FieldResult] = getattr(extraction, attr, None)
        if field and field.value:
            weighted_sum += field.confidence * weight
            weight_total += weight

    if weight_total == 0:
        return 0.0

    base = weighted_sum / weight_total

    # Penalise if any image was POOR quality
    if any(o.quality == "POOR" for o in ocr_results):
        base *= 0.85

    return round(min(1.0, base), 3)


def _encrypt_pii(data: dict, key: str) -> str:
    f = Fernet(key.encode())
    return f.encrypt(json.dumps(data).encode()).decode()


def _decrypt_pii(pii_data: Optional[dict], key: str) -> Optional[PiiData]:
    if not pii_data or "encrypted" not in pii_data:
        return None
    try:
        f = Fernet(key.encode())
        raw = json.loads(f.decrypt(pii_data["encrypted"].encode()).decode())
        return PiiData(phones=raw.get("phones", []), emails=raw.get("emails", []))
    except Exception:
        return None
