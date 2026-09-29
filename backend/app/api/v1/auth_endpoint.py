from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth import get_current_user_id
from app.config import get_settings
from app.db.base import get_db
from app.db.models import User

router = APIRouter()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AuthRequest(BaseModel):
    email: EmailStr
    password: str


class UserInfo(BaseModel):
    id: str
    email: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


# ---------------------------------------------------------------------------
# Password + token helpers
# ---------------------------------------------------------------------------
# bcrypt hashes at most the first 72 bytes; encode then clamp so long inputs
# don't raise. python-jose signs HS256 with the same secret app/auth.py verifies.


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], password_hash.encode("utf-8"))
    except ValueError:
        return False


def _issue_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(tz=timezone.utc)
    claims = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm="HS256")


# ---------------------------------------------------------------------------
# POST /api/v1/auth/signup
# ---------------------------------------------------------------------------


@router.post("/auth/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(body: AuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    email = body.email.lower().strip()
    if len(body.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with that email already exists.")

    user = User(id=uuid.uuid4(), email=email, password_hash=_hash_password(body.password))
    db.add(user)
    db.commit()

    token = _issue_token(user.id)
    return AuthResponse(access_token=token, user=UserInfo(id=str(user.id), email=user.email))


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------


@router.post("/auth/login", response_model=AuthResponse)
def login(body: AuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    email = body.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user or not _verify_password(body.password, user.password_hash):
        # Same message for both cases — don't leak which emails exist.
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = _issue_token(user.id)
    return AuthResponse(access_token=token, user=UserInfo(id=str(user.id), email=user.email))


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------


@router.get("/auth/me", response_model=UserInfo)
def me(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Session = Depends(get_db),
) -> UserInfo:
    user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return UserInfo(id=str(user.id), email=user.email)
