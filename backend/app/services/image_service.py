"""
NameboardImageService — uploads images to ImageKit and returns URLs + file IDs.
"""

import base64
import uuid
from dataclasses import dataclass

import httpx
from fastapi import UploadFile, HTTPException

from app.config import get_settings

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MIN_RESOLUTION_PX = 100  # reject obviously tiny images (width or height)


@dataclass
class ImageUploadResult:
    url: str
    file_id: str
    original_filename: str


async def upload_images(
    files: list[UploadFile], session_id: str
) -> list[ImageUploadResult]:
    if not files:
        raise HTTPException(status_code=400, detail="At least one image is required.")
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 images per request.")

    results = []
    for index, file in enumerate(files):
        _validate_file(file)
        content = await file.read()
        _validate_size(content, file.filename)
        result = await _upload_to_imagekit(
            content, file.filename or f"image_{index}", session_id, index
        )
        results.append(result)

    return results


def _validate_file(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file.content_type}'. Only JPEG and PNG are accepted.",
        )


def _validate_size(content: bytes, filename: str) -> None:
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File '{filename}' exceeds the 10 MB limit.",
        )


async def _upload_to_imagekit(
    content: bytes, filename: str, session_id: str, index: int
) -> ImageUploadResult:
    settings = get_settings()
    folder = f"/nameboards/{session_id}/{index}/"

    # ImageKit upload uses HTTP Basic auth: private_key as username, empty password
    auth = base64.b64encode(f"{settings.imagekit_private_key}:".encode()).decode()

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://upload.imagekit.io/api/v1/files/upload",
            headers={"Authorization": f"Basic {auth}"},
            data={
                "fileName": f"{uuid.uuid4()}_{filename}",
                "folder": folder,
                "useUniqueFileName": "false",
            },
            files={"file": (filename, content)},
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"ImageKit upload failed: {response.text}",
        )

    data = response.json()
    return ImageUploadResult(
        url=data["url"],
        file_id=data["fileId"],
        original_filename=filename,
    )
