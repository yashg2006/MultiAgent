"""
Accounts and sessions.

- Passwords are hashed with bcrypt (8-72 characters; bcrypt ignores bytes
  beyond 72, so longer ones are rejected rather than silently truncated).
- A session is a signed JWT (HS256) in an httpOnly, SameSite=Strict cookie:
  page scripts can't read it, and other sites can't make the browser send it.
  Non-browser clients may instead send `Authorization: Bearer <token>`.
- `current_user` is the FastAPI dependency every protected route uses.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select

from src.api.rate_limit import client_ip, enforce_rate_limit
from src.shared.config import settings
from src.shared.db import UserRecord, session_scope
from src.shared.utils import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "session"
_ALGORITHM = "HS256"
_dev_secret: str | None = None


def signing_key() -> str:
    """The JWT key: JWT_SECRET, or (outside production) a per-process random key."""
    global _dev_secret
    if settings.jwt_secret:
        return settings.jwt_secret
    if settings.env.lower() == "production":
        raise RuntimeError("JWT_SECRET must be set when ENV=production.")
    if _dev_secret is None:
        _dev_secret = secrets.token_urlsafe(32)
        logger.warning("JWT_SECRET not set; using a random key (sessions end on restart).")
    return _dev_secret


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


_dummy_hash: str | None = None


def _equal_work_hash() -> str:
    """A real bcrypt hash to check against when the email is unknown, so a
    failed sign-in takes the same time either way (no account enumeration)."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password(secrets.token_urlsafe(16))
    return _dummy_hash


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


def create_token(user_id: str, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    claims = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(claims, signing_key(), algorithm=_ALGORITHM)


def decode_token(token: str) -> str | None:
    """The user id in a valid, unexpired token; None otherwise."""
    try:
        claims = jwt.decode(token, signing_key(), algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
    subject = claims.get("sub")
    return subject if isinstance(subject, str) else None


class Credentials(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., min_length=8)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        value = value.strip().lower()
        local, _, domain = value.partition("@")
        if not local or "." not in domain or " " in value:
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes.")
        return value


class UserOut(BaseModel):
    id: str
    email: str
    created_at: datetime


def _to_user_out(record: UserRecord) -> UserOut:
    return UserOut(id=record.id, email=record.email, created_at=record.created_at)


def _set_session_cookie(response: Response, user_id: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        create_token(user_id),
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path="/",
    )


def _token_from(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return request.cookies.get(COOKIE_NAME)


async def current_user(request: Request) -> UserOut:
    """Dependency: the signed-in user, or HTTP 401."""
    token = _token_from(request)
    user_id = decode_token(token) if token else None
    if user_id is None:
        raise HTTPException(status_code=401, detail="Sign in to continue.")

    def load() -> UserOut | None:
        with session_scope() as session:
            record = session.get(UserRecord, user_id)
            return _to_user_out(record) if record else None

    user = await run_in_threadpool(load)
    if user is None:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    return user


@router.post("/register", response_model=UserOut, status_code=201)
async def register(credentials: Credentials, request: Request, response: Response) -> UserOut:
    """Create an account and sign in."""
    await enforce_rate_limit(
        request, f"auth:{client_ip(request)}", settings.auth_rate_limit_per_minute
    )
    password_hash = await run_in_threadpool(hash_password, credentials.password)

    def create() -> UserOut | None:
        with session_scope() as session:
            taken = session.scalar(
                select(func.count())
                .select_from(UserRecord)
                .where(UserRecord.email == credentials.email)
            )
            if taken:
                return None
            record = UserRecord(
                id=str(uuid.uuid4()), email=credentials.email, password_hash=password_hash
            )
            session.add(record)
            session.flush()
            return _to_user_out(record)

    user = await run_in_threadpool(create)
    if user is None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    _set_session_cookie(response, user.id)
    return user


@router.post("/login", response_model=UserOut)
async def login(credentials: Credentials, request: Request, response: Response) -> UserOut:
    """Sign in. The error doesn't say whether the email or the password was wrong."""
    await enforce_rate_limit(
        request, f"auth:{client_ip(request)}", settings.auth_rate_limit_per_minute
    )

    def check() -> UserOut | None:
        with session_scope() as session:
            record = session.scalar(select(UserRecord).where(UserRecord.email == credentials.email))
            stored_hash = record.password_hash if record else _equal_work_hash()
            if not verify_password(credentials.password, stored_hash) or record is None:
                return None
            return _to_user_out(record)

    user = await run_in_threadpool(check)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    _set_session_cookie(response, user.id)
    return user


@router.post("/logout", status_code=204)
def logout(response: Response) -> Response:
    """Sign out (clears the session cookie)."""
    response.delete_cookie(
        COOKIE_NAME, path="/", httponly=True, secure=settings.cookie_secure, samesite="strict"
    )
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut)
async def me(user: UserOut = Depends(current_user)) -> UserOut:
    """The signed-in user (401 if signed out)."""
    return user
