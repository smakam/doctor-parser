"""
Basic tests for the nameboard extraction pipeline.
External services (ImageKit, Google Vision, OpenAI, Mappls) are mocked.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def mock_settings(monkeypatch):
    """Provide dummy settings so tests don't need a real .env file."""
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()

    env = {
        "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/testdb",
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_JWT_SECRET": "test-jwt-secret",
        "GOOGLE_VISION_API_KEY": "test-vision-key",
        "OPENAI_API_KEY": "test-openai-key",
        "IMAGEKIT_PUBLIC_KEY": "test-public",
        "IMAGEKIT_PRIVATE_KEY": "test-private",
        "IMAGEKIT_URL_ENDPOINT": "https://ik.imagekit.io/test",
        "MAPPLS_CLIENT_ID": "test-id",
        "MAPPLS_CLIENT_SECRET": "test-secret",
        "PII_ENCRYPTION_KEY": key,
        "SECRET_KEY": "test-secret-key",
        "ENVIRONMENT": "test",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)

    # Clear lru_cache so fresh settings are loaded
    from app.config import get_settings
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_health(mock_settings):
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_compute_overall_confidence():
    from app.services.extraction_service import ExtractionResult, FieldResult
    from app.services.ocr_service import ImageOcrResult
    from app.services.result_service import _compute_overall_confidence

    extraction = ExtractionResult(
        doctor_name=FieldResult(value="Dr. Test", confidence=0.95),
        address=FieldResult(value="123 Test St", confidence=0.80),
        medical_registration_no=FieldResult(value="MH-12345", confidence=0.90),
    )
    ocr_results = [
        ImageOcrResult(
            imagekit_url="https://example.com/img.jpg",
            raw_text="Dr. Test\n123 Test St\nMH-12345",
            text_density=10.0,
            average_word_confidence=0.88,
            detected_languages=["en"],
            quality="GOOD",
        )
    ]

    confidence = _compute_overall_confidence(extraction, ocr_results)
    assert 0.0 < confidence <= 1.0


def test_poor_image_penalises_confidence():
    from app.services.extraction_service import ExtractionResult, FieldResult
    from app.services.ocr_service import ImageOcrResult
    from app.services.result_service import _compute_overall_confidence

    extraction = ExtractionResult(
        doctor_name=FieldResult(value="Dr. Test", confidence=0.95),
    )
    good_ocr = ImageOcrResult(
        imagekit_url="https://example.com/good.jpg",
        raw_text="Dr. Test",
        text_density=10.0,
        average_word_confidence=0.95,
        detected_languages=["en"],
        quality="GOOD",
    )
    poor_ocr = ImageOcrResult(
        imagekit_url="https://example.com/poor.jpg",
        raw_text="blurry",
        text_density=2.0,
        average_word_confidence=0.30,
        detected_languages=["en"],
        quality="POOR",
    )

    good_confidence = _compute_overall_confidence(extraction, [good_ocr])
    penalised_confidence = _compute_overall_confidence(extraction, [good_ocr, poor_ocr])
    assert penalised_confidence < good_confidence


def test_pii_encrypt_decrypt():
    from cryptography.fernet import Fernet
    from app.services.result_service import _encrypt_pii, _decrypt_pii

    key = Fernet.generate_key().decode()
    pii = {"phones": ["9876543210"], "emails": ["doctor@example.com"]}

    encrypted = _encrypt_pii(pii, key)
    pii_data_record = {"encrypted": encrypted}
    decrypted = _decrypt_pii(pii_data_record, key)

    assert decrypted is not None
    assert decrypted.phones == ["9876543210"]
    assert decrypted.emails == ["doctor@example.com"]
