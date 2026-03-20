import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Numeric, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class NameboardExtraction(Base):
    __tablename__ = "nameboard_extractions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String, nullable=False, index=True)
    uploaded_by_customer_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    uploaded_by_posp_id = Column(UUID(as_uuid=True), nullable=True)

    imagekit_file_ids = Column(JSONB)          # list of ImageKit file IDs
    images_processed = Column(Integer)
    overall_confidence = Column(Numeric(4, 3))

    extracted_data = Column(JSONB)             # non-PII fields with confidence scores
    pii_data = Column(JSONB)                   # encrypted phone/email fields
    image_quality = Column(JSONB)              # per-image quality assessments
    extraction_warnings = Column(JSONB)        # list of warning strings

    geocoding_status = Column(String)          # FULL_ADDRESS / PIN_CODE_CENTROID / ADDRESS_ONLY / NOT_GEOCODED

    status = Column(String, default="PENDING_REVIEW")  # PENDING_REVIEW / ACCEPTED / REJECTED
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
