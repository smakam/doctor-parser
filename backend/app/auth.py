import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx
from fastapi import Header
from jose import jwt, JWTError

from app.config import get_settings

logger = logging.getLogger(__name__)

# Simple in-memory JWKS cache — refreshed every hour
_jwks_cache: dict = {"keys": [], "fetched_at": 0}
_JWKS_TTL = 3600  # seconds


async def _get_jwks() -> dict:
    now = time.time()
    if now - _jwks_cache["fetched_at"] < _JWKS_TTL and _jwks_cache["keys"]:
        return _jwks_cache

    settings = get_settings()
    url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

    _jwks_cache["keys"] = data.get("keys", [])
    _jwks_cache["fetched_at"] = now
    return _jwks_cache


async def _verify_supabase_jwt(token: str) -> dict:
    jwks = await _get_jwks()
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")

    # Find the matching public key by kid
    key = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
    if not key and jwks["keys"]:
        key = jwks["keys"][0]  # fallback: use first key if kid not found
    if not key:
        raise JWTError("No public key available in Supabase JWKS")

    return jwt.decode(token, key, algorithms=["RS256"], options={"verify_aud": False})


@dataclass
class UserContext:
    id: str
    role: str = "authenticated"
    is_guest: bool = False


async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    x_guest_session: Optional[str] = Header(None),
) -> Optional[UserContext]:
    """
    Returns authenticated user from Supabase JWT (RS256), guest context from
    session header, or None if neither is present.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            payload = await _verify_supabase_jwt(token)
            return UserContext(id=payload["sub"], role=payload.get("role", "authenticated"))
        except (JWTError, Exception) as e:
            logger.warning("JWT verification failed: %s", e)

    if x_guest_session:
        return UserContext(id=x_guest_session, role="guest", is_guest=True)

    return None


async def get_current_user_required(
    authorization: Optional[str] = Header(None),
    x_guest_session: Optional[str] = Header(None),
) -> UserContext:
    user = await get_current_user_optional(authorization, x_guest_session)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
