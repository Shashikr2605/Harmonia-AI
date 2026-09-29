from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import get_settings

# ---------------------------------------------------------------------------
# NOTE on Supabase JWT signing algorithm
# ---------------------------------------------------------------------------
# Supabase's legacy projects use HS256 with a shared "JWT Secret" (shown at
# Project Settings → API → JWT Secret).  Newer projects may switch to ES256
# (asymmetric, verified via the JWKS endpoint at
#   {SUPABASE_URL}/auth/v1/.well-known/jwks.json).
#
# This implementation uses HS256 + JWT_SECRET env var, which covers the
# majority of Supabase setups.  If you see "JWTError: Invalid algorithm" at
# runtime, your project uses ES256 — swap the decode call below for a JWKS
# fetch + RSA verify (see python-jose docs).
# ---------------------------------------------------------------------------

_security = HTTPBearer()


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_security)],
) -> str:
    """
    FastAPI dependency.  Verifies the Supabase JWT and returns the user UUID
    string extracted from the ``sub`` claim.

    Raises HTTP 401 on any verification failure.
    """
    settings = get_settings()
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=["HS256"],
            # Supabase tokens carry audience "authenticated" — we verify sub only
            options={"verify_aud": False},
        )
    except JWTError as exc_inner:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token error: {exc_inner}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc_inner

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise exc

    return user_id
