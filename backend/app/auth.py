from dataclasses import dataclass
from typing import Optional
from fastapi import Header
from jose import jwt, JWTError
from app.config import get_settings


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
    Returns authenticated user from Supabase JWT, guest context from session header,
    or None if neither is present.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
        try:
            settings = get_settings()
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
            return UserContext(id=payload["sub"], role=payload.get("role", "authenticated"))
        except JWTError:
            pass

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
