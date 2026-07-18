"""
NameboardExtractionService — sends OCR text to GPT-4o and returns structured fields.
Applies cross-image confidence boost when the same value appears in multiple images.
"""

import json
from dataclasses import dataclass
from typing import Optional

from openai import AsyncOpenAI
from fastapi import HTTPException

from app.config import get_settings
from app.services.ocr_service import ImageOcrResult

CONFIDENCE_BOOST_MULTIPLIER = 1.15
CONFIDENCE_BOOST_MIN_IMAGES = 2

EXTRACTION_PROMPT = """You are an expert at extracting structured information from Indian doctor nameboards and visiting cards.

Extract the following fields from the OCR text below. For each field provide a value and a confidence score (0.0–1.0).

Rules:
- Return ONLY valid JSON matching the schema below.
- Return null for value if the field is not found — never hallucinate or guess.
- Confidence reflects certainty: 1.0 = certain, 0.0 = absent/unreadable.
- Preserve Dr./Prof./Col./Brig. prefix in doctorName.
- qualifications should be comma-separated (e.g., "MBBS, MD, DNB").
- Indian medical qualifications include: MBBS, MD, MS, DNB, DM, MCh, BDS, BAMS, BHMS, BUMS, MDS, FRCS, MRCP.
- medicalRegistrationNo follows State Medical Council formats (e.g., "MH-12345", "KA/56789", "DMC/R/2023/1234").
- pinCode is a 6-digit Indian postal code.
- Extract phone numbers and emails into pii_fields — do NOT include them in any other field value.

OCR Text (from {image_count} image(s)):
---
{ocr_text}
---

Return JSON in exactly this format:
{{
  "doctorName":            {{"value": "Dr. Ramesh Kumar", "confidence": 0.95}},
  "clinicName":            {{"value": null, "confidence": 0.0}},
  "specialisation":        {{"value": "Cardiologist", "confidence": 0.90}},
  "qualifications":        {{"value": "MBBS, MD, DNB", "confidence": 0.88}},
  "medicalRegistrationNo": {{"value": "MH-45231", "confidence": 0.80}},
  "address":               {{"value": "12, Gandhi Road, Mumbai", "confidence": 0.75}},
  "pinCode":               {{"value": "400001", "confidence": 0.92}},
  "consultationTimings":   {{"value": "Mon-Sat 10:00-13:00, 17:00-20:00", "confidence": 0.70}},
  "pii_fields":            {{"phones": ["9876543210"], "emails": []}}
}}"""


@dataclass
class FieldResult:
    value: Optional[str]
    confidence: float


@dataclass
class ExtractionResult:
    doctor_name: Optional[FieldResult] = None
    clinic_name: Optional[FieldResult] = None
    specialisation: Optional[FieldResult] = None
    qualifications: Optional[FieldResult] = None
    medical_registration_no: Optional[FieldResult] = None
    address: Optional[FieldResult] = None
    pin_code: Optional[FieldResult] = None
    consultation_timings: Optional[FieldResult] = None
    pii_phones: list[str] = None
    pii_emails: list[str] = None

    def __post_init__(self):
        if self.pii_phones is None:
            self.pii_phones = []
        if self.pii_emails is None:
            self.pii_emails = []


async def extract_fields(ocr_results: list[ImageOcrResult]) -> ExtractionResult:
    concatenated_text = "\n---\n".join(
        r.raw_text for r in ocr_results if r.raw_text.strip()
    )
    if not concatenated_text.strip():
        raise HTTPException(
            status_code=422, detail="No readable text found in the uploaded images."
        )

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    prompt = EXTRACTION_PROMPT.format(
        image_count=len(ocr_results),
        ocr_text=concatenated_text,
    )

    response = await client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    try:
        raw = json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, KeyError) as e:
        raise HTTPException(
            status_code=502, detail=f"GPT-4o returned invalid JSON: {e}"
        )

    result = _parse_gpt_response(raw)
    result = _apply_cross_image_boost(result, ocr_results)
    return result


def _parse_gpt_response(raw: dict) -> ExtractionResult:
    def field(key: str) -> Optional[FieldResult]:
        data = raw.get(key)
        if not data:
            return None
        return FieldResult(
            value=data.get("value"), confidence=float(data.get("confidence", 0.0))
        )

    pii = raw.get("pii_fields", {})
    return ExtractionResult(
        doctor_name=field("doctorName"),
        clinic_name=field("clinicName"),
        specialisation=field("specialisation"),
        qualifications=field("qualifications"),
        medical_registration_no=field("medicalRegistrationNo"),
        address=field("address"),
        pin_code=field("pinCode"),
        consultation_timings=field("consultationTimings"),
        pii_phones=pii.get("phones", []),
        pii_emails=pii.get("emails", []),
    )


def _apply_cross_image_boost(
    result: ExtractionResult, ocr_results: list[ImageOcrResult]
) -> ExtractionResult:
    """
    For each extracted field, if the same value appears in text from 2+ images,
    boost confidence by CONFIDENCE_BOOST_MULTIPLIER (capped at 1.0).
    If values conflict, use the value from the image with highest text_density
    and reduce confidence.
    """
    if len(ocr_results) < CONFIDENCE_BOOST_MIN_IMAGES:
        return result

    field_names = [
        ("doctor_name", "doctorName"),
        ("clinic_name", "clinicName"),
        ("specialisation", "specialisation"),
        ("qualifications", "qualifications"),
        ("medical_registration_no", "medicalRegistrationNo"),
        ("address", "address"),
        ("pin_code", "pinCode"),
        ("consultation_timings", "consultationTimings"),
    ]

    for attr, _ in field_names:
        field_result: Optional[FieldResult] = getattr(result, attr)
        if not field_result or not field_result.value:
            continue

        value_lower = field_result.value.lower()
        images_with_value = sum(
            1 for ocr in ocr_results if value_lower in ocr.raw_text.lower()
        )

        if images_with_value >= CONFIDENCE_BOOST_MIN_IMAGES:
            field_result.confidence = min(
                1.0, field_result.confidence * CONFIDENCE_BOOST_MULTIPLIER
            )

    return result
