from typing import Optional
from fastapi import FastAPI, Header
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import nameboard
from app.auth import get_current_user_optional

settings = get_settings()

app = FastAPI(
    title="Doctor Nameboard Extractor",
    version="1.0.0",
    description="Extract structured doctor profile data from nameboard photos using AI.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nameboard.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug/auth")
async def debug_auth(
    authorization: Optional[str] = Header(None),
    x_guest_session: Optional[str] = Header(None),
):
    user = await get_current_user_optional(authorization, x_guest_session)
    return {
        "auth_header_present": bool(authorization),
        "user_resolved": user is not None,
        "user_id": user.id if user else None,
        "user_role": user.role if user else None,
        "is_guest": user.is_guest if user else None,
    }
