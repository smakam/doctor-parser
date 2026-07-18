"""
NameboardOcrService — runs Google Cloud Vision Document Text Detection on image URLs.
Returns per-image raw text, confidence scores, detected languages, and quality flags.
"""

import asyncio
from dataclasses import dataclass, field

import httpx
from fastapi import HTTPException

from app.config import get_settings

POOR_QUALITY_THRESHOLD = 0.5
VISION_API_URL = "https://vision.googleapis.com/v1/images:annotate"


@dataclass
class WordBlock:
    text: str
    confidence: float
    bounding_box: dict


@dataclass
class ImageOcrResult:
    imagekit_url: str
    raw_text: str
    text_density: float  # characters per 1000px² (approximation)
    average_word_confidence: float
    detected_languages: list[str]
    quality: str  # GOOD / POOR
    word_blocks: list[WordBlock] = field(default_factory=list)


async def extract_text_all(urls: list[str]) -> list[ImageOcrResult]:
    """Run OCR on all images in parallel."""
    return await asyncio.gather(*[extract_text(url) for url in urls])


async def extract_text(image_url: str) -> ImageOcrResult:
    settings = get_settings()

    payload = {
        "requests": [
            {
                "image": {"source": {"imageUri": image_url}},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                "imageContext": {"languageHints": ["en", "hi", "ta", "te", "kn", "mr"]},
            }
        ]
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            VISION_API_URL,
            params={"key": settings.google_vision_api_key},
            json=payload,
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502, detail=f"Google Vision API error: {response.text}"
        )

    data = response.json()
    annotation = data.get("responses", [{}])[0]

    if "error" in annotation:
        raise HTTPException(
            status_code=502, detail=f"Vision API error: {annotation['error']}"
        )

    return _parse_annotation(image_url, annotation)


def _parse_annotation(image_url: str, annotation: dict) -> ImageOcrResult:
    full_text_annotation = annotation.get("fullTextAnnotation", {})
    raw_text = full_text_annotation.get("text", "")

    detected_languages: list[str] = []
    word_blocks: list[WordBlock] = []
    confidence_scores: list[float] = []

    for page in full_text_annotation.get("pages", []):
        for lang in page.get("property", {}).get("detectedLanguages", []):
            code = lang.get("languageCode", "")
            if code and code not in detected_languages:
                detected_languages.append(code)

        for block in page.get("blocks", []):
            for paragraph in block.get("paragraphs", []):
                for word in paragraph.get("words", []):
                    word_text = "".join(
                        s.get("text", "") for s in word.get("symbols", [])
                    )
                    confidence = word.get("confidence", 0.0)
                    bounding_box = word.get("boundingBox", {})

                    word_blocks.append(WordBlock(word_text, confidence, bounding_box))
                    confidence_scores.append(confidence)

    avg_confidence = (
        sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
    )
    text_density = len(raw_text) / max(1, len(word_blocks))  # chars per word as proxy
    quality = "POOR" if avg_confidence < POOR_QUALITY_THRESHOLD else "GOOD"

    return ImageOcrResult(
        imagekit_url=image_url,
        raw_text=raw_text,
        text_density=text_density,
        average_word_confidence=avg_confidence,
        detected_languages=detected_languages,
        quality=quality,
        word_blocks=word_blocks,
    )
