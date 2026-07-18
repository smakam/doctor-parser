"""
NameboardReviewService — handles accept, reject, and correct operations after
a user reviews the extraction result.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.nameboard import NameboardExtraction
from app.schemas.nameboard import CorrectRequest, ExtractedField


async def accept(record: NameboardExtraction, db: AsyncSession) -> NameboardExtraction:
    record.status = "ACCEPTED"
    record.reviewed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(record)
    return record


async def reject(record: NameboardExtraction, db: AsyncSession) -> NameboardExtraction:
    record.status = "REJECTED"
    record.reviewed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(record)
    return record


async def correct(
    record: NameboardExtraction,
    corrections: CorrectRequest,
    db: AsyncSession,
) -> NameboardExtraction:
    """
    Apply user-submitted field corrections. Preserves original extracted values
    and confidence scores alongside the corrections for audit purposes.
    """
    current_data: dict = dict(record.extracted_data or {})

    field_map = {
        "doctor_name": "doctor_name",
        "clinic_name": "clinic_name",
        "specialisation": "specialisation",
        "qualifications": "qualifications",
        "medical_registration_no": "qualifications",
        "address": "address",
        "pin_code": "pin_code",
        "consultation_timings": "consultation_timings",
    }

    for correction_attr, data_key in field_map.items():
        corrected_value: Optional[str] = getattr(corrections, correction_attr, None)
        if corrected_value is None:
            continue

        existing = current_data.get(data_key, {})
        # Preserve original under _original key for audit trail
        if existing and "value" in existing and "_original" not in existing:
            existing["_original"] = {
                "value": existing.get("value"),
                "confidence": existing.get("confidence"),
            }
        existing["value"] = corrected_value
        existing["confidence"] = 1.0  # user-confirmed = max confidence
        existing["corrected"] = True
        current_data[data_key] = existing

    record.extracted_data = current_data
    record.status = "ACCEPTED"
    record.reviewed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(record)
    return record
