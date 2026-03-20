from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ExtractedField(BaseModel):
    value: Optional[str]
    confidence: float


class ExtractedData(BaseModel):
    doctor_name: Optional[ExtractedField] = None
    clinic_name: Optional[ExtractedField] = None
    specialisation: Optional[ExtractedField] = None
    qualifications: Optional[ExtractedField] = None
    medical_registration_no: Optional[ExtractedField] = None
    address: Optional[ExtractedField] = None
    pin_code: Optional[ExtractedField] = None
    consultation_timings: Optional[ExtractedField] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None


class ImageQualityResult(BaseModel):
    imagekit_url: str
    average_word_confidence: float
    text_density: float
    quality: str  # GOOD / POOR
    detected_languages: list[str]
    warnings: list[str]


class PiiData(BaseModel):
    phones: list[str]
    emails: list[str]


class ExtractionResponse(BaseModel):
    id: str
    session_id: str
    images_processed: int
    overall_confidence: float
    extracted_data: ExtractedData
    image_quality: list[ImageQualityResult]
    extraction_warnings: list[str]
    geocoding_status: str
    status: str
    pii_data: Optional[PiiData] = None  # returned only to the uploader
    created_at: datetime


class CorrectRequest(BaseModel):
    doctor_name: Optional[str] = None
    clinic_name: Optional[str] = None
    specialisation: Optional[str] = None
    qualifications: Optional[str] = None
    medical_registration_no: Optional[str] = None
    address: Optional[str] = None
    pin_code: Optional[str] = None
    consultation_timings: Optional[str] = None
