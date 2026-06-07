"""
JWT Authentication, Password Hashing, and RBAC
"""
import hmac
import hashlib
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.db.session import get_db
from app.models.models import User, UserRole

# ============================================================
# PASSWORD HASHING
# ============================================================

import bcrypt

def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


# ============================================================
# JWT TOKENS
# ============================================================

bearer_scheme = HTTPBearer()


def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================================
# DEPENDENCY: Get Current User
# ============================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")

    result = await db.execute(select(User).where(User.id == UUID(user_id), User.is_active == True))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


# ============================================================
# RBAC Role Guards
# ============================================================

def require_role(*roles: UserRole):
    """Factory: returns a dependency that enforces role membership."""
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {[r.value for r in roles]}",
            )
        return user
    return _check


# Convenience guards
require_student   = require_role(UserRole.student)
require_professor = require_role(UserRole.professor)
require_head      = require_role(UserRole.head)
require_prof_or_head = require_role(UserRole.professor, UserRole.head)


# ============================================================
# LIVENESS TOKEN (HMAC-SHA256)
# ============================================================

def generate_liveness_token(challenge: str, student_id: str) -> str:
    """Generate a time-bound liveness token signed with HMAC-SHA256."""
    timestamp = int(time.time())
    message = f"{student_id}:{challenge}:{timestamp}"
    sig = hmac.new(
        settings.LIVENESS_TOKEN_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"{timestamp}:{sig}"


def verify_liveness_token(token: str, challenge: str, student_id: str) -> bool:
    """Verify liveness token is fresh and authentic."""
    try:
        timestamp_str, received_sig = token.split(":", 1)
        timestamp = int(timestamp_str)
    except (ValueError, AttributeError):
        return False

    # Check freshness
    if time.time() - timestamp > settings.LIVENESS_TOKEN_TTL_SECONDS:
        return False

    # Verify signature
    message = f"{student_id}:{challenge}:{timestamp}"
    expected_sig = hmac.new(
        settings.LIVENESS_TOKEN_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(received_sig, expected_sig)
