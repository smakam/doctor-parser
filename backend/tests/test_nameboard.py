"""
Tests for the nameboard extraction pipeline.
External services (ImageKit, Google Vision, OpenAI, Mappls) are mocked.
"""

import uuid
import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def fernet_key():
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()


@pytest.fixture
def mock_settings(monkeypatch, fernet_key):
    env = {
        "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/testdb",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "GOOGLE_VISION_API_KEY": "test-vision-key",
        "OPENAI_API_KEY": "test-openai-key",
        "IMAGEKIT_PUBLIC_KEY": "test-public",
        "IMAGEKIT_PRIVATE_KEY": "test-private",
        "IMAGEKIT_URL_ENDPOINT": "https://ik.imagekit.io/test",
        "MAPPLS_API_KEY": "",
        "PII_ENCRYPTION_KEY": fernet_key,
        "SECRET_KEY": "test-secret-key",
        "ENVIRONMENT": "test",
        "CORS_ORIGINS": "http://localhost:5173",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    from app.config import get_settings

    get_settings.cache_clear()


@pytest.fixture
def sample_extraction_result():
    from app.services.extraction_service import ExtractionResult, FieldResult

    return ExtractionResult(
        doctor_name=FieldResult(value="Dr. Priya Sharma", confidence=0.98),
        clinic_name=FieldResult(value="Sharma Clinic", confidence=0.95),
        specialisation=FieldResult(value="General Physician", confidence=0.92),
        qualifications=FieldResult(value="MBBS, MD", confidence=0.90),
        medical_registration_no=FieldResult(value="MH-12345", confidence=0.95),
        address=FieldResult(value="123 MG Road, Mumbai", confidence=0.88),
        pin_code=FieldResult(value="400001", confidence=0.95),
        consultation_timings=FieldResult(value="9am-6pm Mon-Sat", confidence=0.85),
        pii_phones=["9876543210"],
        pii_emails=["dr.sharma@example.com"],
    )


@pytest.fixture
def sample_ocr_result():
    from app.services.ocr_service import ImageOcrResult

    return ImageOcrResult(
        imagekit_url="https://ik.imagekit.io/test/img.jpg",
        raw_text="Dr. Priya Sharma\nMBBS, MD\n123 MG Road Mumbai\n9876543210",
        text_density=8.5,
        average_word_confidence=0.93,
        detected_languages=["en"],
        quality="GOOD",
    )


# ── Health & auth ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health(mock_settings):
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_debug_auth_no_headers(mock_settings):
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/debug/auth")
    assert r.status_code == 200
    data = r.json()
    assert data["user_resolved"] is False
    assert data["user_id"] is None


@pytest.mark.asyncio
async def test_debug_auth_guest_session(mock_settings):
    from app.main import app

    guest_id = str(uuid.uuid4())
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get("/debug/auth", headers={"X-Guest-Session": guest_id})
    assert r.status_code == 200
    data = r.json()
    assert data["user_resolved"] is True
    assert data["user_id"] == guest_id
    assert data["is_guest"] is True


# ── Access control ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_extraction_requires_auth(mock_settings):
    """GET /api/nameboard/{id} returns 401 when no auth provided."""
    from app.main import app
    from app.database import get_db

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    fake_id = str(uuid.uuid4())
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.get(f"/api/nameboard/{fake_id}")
        assert r.status_code == 401
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_accept_requires_auth(mock_settings):
    from app.main import app
    from app.database import get_db

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    fake_id = str(uuid.uuid4())
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(f"/api/nameboard/{fake_id}/accept")
        assert r.status_code == 401
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_history_requires_real_auth(mock_settings):
    """GET /api/nameboard returns 401 for guests and unauthenticated requests."""
    from app.main import app

    guest_id = str(uuid.uuid4())
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # No auth
        r1 = await client.get("/api/nameboard")
        assert r1.status_code == 401

        # Guest session — also rejected
        r2 = await client.get("/api/nameboard", headers={"X-Guest-Session": guest_id})
        assert r2.status_code == 401


# ── Service unit tests ─────────────────────────────────────────────────────────


def test_compute_overall_confidence(sample_extraction_result, sample_ocr_result):
    from app.services.result_service import _compute_overall_confidence

    confidence = _compute_overall_confidence(
        sample_extraction_result, [sample_ocr_result]
    )
    assert 0.0 < confidence <= 1.0


def test_poor_image_penalises_confidence(sample_extraction_result):
    from app.services.ocr_service import ImageOcrResult
    from app.services.result_service import _compute_overall_confidence

    good = ImageOcrResult(
        imagekit_url="https://example.com/good.jpg",
        raw_text="Dr. Test",
        text_density=10.0,
        average_word_confidence=0.95,
        detected_languages=["en"],
        quality="GOOD",
    )
    poor = ImageOcrResult(
        imagekit_url="https://example.com/poor.jpg",
        raw_text="blurry",
        text_density=2.0,
        average_word_confidence=0.30,
        detected_languages=["en"],
        quality="POOR",
    )
    good_conf = _compute_overall_confidence(sample_extraction_result, [good])
    penalised = _compute_overall_confidence(sample_extraction_result, [good, poor])
    assert penalised < good_conf


def test_pii_encrypt_decrypt(fernet_key):
    from app.services.result_service import _encrypt_pii, _decrypt_pii

    pii = {"phones": ["9876543210"], "emails": ["doctor@example.com"]}
    encrypted = _encrypt_pii(pii, fernet_key)
    decrypted = _decrypt_pii({"encrypted": encrypted}, fernet_key)
    assert decrypted is not None
    assert decrypted.phones == ["9876543210"]
    assert decrypted.emails == ["doctor@example.com"]


def test_pii_decrypt_bad_data(fernet_key):
    from app.services.result_service import _decrypt_pii

    assert _decrypt_pii(None, fernet_key) is None
    assert _decrypt_pii({}, fernet_key) is None
    assert _decrypt_pii({"encrypted": "not-valid-fernet"}, fernet_key) is None


def test_build_warnings_missing_name():
    from app.services.extraction_service import ExtractionResult
    from app.services.ocr_service import ImageOcrResult
    from app.services.result_service import _build_warnings

    extraction = ExtractionResult()  # no fields
    ocr = [
        ImageOcrResult(
            imagekit_url="u",
            raw_text="text",
            text_density=1.0,
            average_word_confidence=0.9,
            detected_languages=["en"],
            quality="GOOD",
        )
    ]
    warnings = _build_warnings(ocr, extraction)
    assert any("Doctor name" in w for w in warnings)
    assert any("Address" in w for w in warnings)


def test_build_warnings_poor_image():
    from app.services.extraction_service import ExtractionResult, FieldResult
    from app.services.ocr_service import ImageOcrResult
    from app.services.result_service import _build_warnings

    extraction = ExtractionResult(
        doctor_name=FieldResult(value="Dr. X", confidence=0.9),
        address=FieldResult(value="123 St", confidence=0.9),
    )
    ocr = [
        ImageOcrResult(
            imagekit_url="u",
            raw_text="blurry",
            text_density=1.0,
            average_word_confidence=0.3,
            detected_languages=["en"],
            quality="POOR",
        )
    ]
    warnings = _build_warnings(ocr, extraction)
    assert any("low OCR confidence" in w for w in warnings)


def test_overall_confidence_zero_when_no_fields():
    from app.services.extraction_service import ExtractionResult
    from app.services.result_service import _compute_overall_confidence

    assert _compute_overall_confidence(ExtractionResult(), []) == 0.0


# ── Result assembly ────────────────────────────────────────────────────────────


def test_build_extracted_data(sample_extraction_result):
    from app.services.geocoding_service import GeocodingResult
    from app.services.result_service import _build_extracted_data

    geo = GeocodingResult(
        geocoding_status="PIN_CODE_CENTROID",
        latitude=19.076,
        longitude=72.877,
        city="Mumbai",
        state="Maharashtra",
        geocoding_confidence=0.9,
    )
    data = _build_extracted_data(sample_extraction_result, geo)
    assert data.doctor_name.value == "Dr. Priya Sharma"
    assert data.latitude == 19.076
    assert data.city == "Mumbai"


def test_build_response_hides_pii_for_wrong_user(fernet_key, monkeypatch):
    import uuid as _uuid
    import datetime
    from app.services.result_service import _encrypt_pii, build_response
    from app.models.nameboard import NameboardExtraction
    from app.schemas.nameboard import ExtractedData

    owner_id = str(_uuid.uuid4())
    other_id = str(_uuid.uuid4())
    encrypted = _encrypt_pii({"phones": ["9999999999"], "emails": []}, fernet_key)

    record = NameboardExtraction(
        id=_uuid.uuid4(),
        session_id=owner_id,
        uploaded_by_customer_id=_uuid.UUID(owner_id),
        images_processed=1,
        overall_confidence=0.95,
        extracted_data=ExtractedData().model_dump(),
        pii_data={"encrypted": encrypted},
        image_quality=[],
        extraction_warnings=[],
        geocoding_status="NOT_GEOCODED",
        status="PENDING_REVIEW",
        created_at=datetime.datetime.utcnow(),
    )

    # Owner sees PII
    resp_owner = build_response(record, owner_id, fernet_key)
    assert resp_owner.pii_data is not None
    assert "9999999999" in resp_owner.pii_data.phones

    # Other user does not see PII
    resp_other = build_response(record, other_id, fernet_key)
    assert resp_other.pii_data is None
