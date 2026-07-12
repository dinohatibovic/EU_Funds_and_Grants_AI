"""
backend/app/core/security.py — Autentifikacija i sigurnosne primitive.

Password hashing (SHA256 + salt), JWT kreiranje/verifikacija i FastAPI
dependency za zaštićene endpointe.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.core import config


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{h}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split(":", 1)
    if len(parts) != 2:
        return False
    salt, h = parts
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest() == h


def create_jwt(email: str) -> str:
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=config.JWT_EXPIRE_DAYS)
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    """Dekodira JWT — baca HTTPException 401 za istekle/neispravne tokene."""
    try:
        return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token je istekao.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Neispravan token.")


_http_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_http_bearer),
) -> str:
    """JWT dependency — provjera Bearer tokena na zaštićenim endpointima."""
    payload = decode_jwt(credentials.credentials)
    return payload["sub"]
