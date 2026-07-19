"""
backend/app/api/auth.py — Registracija, prijava i provjera sesije.
"""

import logging
import sqlite3

from fastapi import APIRouter, HTTPException, Request

from backend.app.api.schemas import AuthResponse, LoginRequest, RegisterRequest
from backend.app.core.database import db_ctx, db_exec, ph
from backend.app.core.security import create_jwt, decode_jwt, hash_password, verify_password

logger = logging.getLogger("eu_grants_api")

router = APIRouter()


@router.post("/auth/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    """Registracija novog korisnika. Validacija emaila i lozinke je u Pydantic modelu."""
    email = req.email  # već normalizovan u validator-u
    try:
        with db_ctx() as (conn, cf):
            db_exec(conn, cf,
                f"INSERT INTO users (email, password_hash) VALUES ({ph()}, {ph()})",  # nosec B608 — ph() je samo placeholder (?/%s), vrijednosti su parametrizovane
                (email, hash_password(req.password))
            )
    except Exception as e:
        if isinstance(e, sqlite3.IntegrityError) or "unique" in str(e).lower() or "duplicate" in str(e).lower():
            raise HTTPException(status_code=409, detail="Korisnik s ovim emailom već postoji.")
        raise
    logger.info(f"✅ Novi korisnik registrovan: {email}")
    return AuthResponse(token=create_jwt(email), email=email, plan="free")


@router.post("/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    """Prijava korisnika."""
    email = req.email.strip().lower()
    with db_ctx() as (conn, cf):
        row = db_exec(conn, cf, f"SELECT * FROM users WHERE email = {ph()}", (email,)).fetchone()  # nosec B608 — ph() je placeholder, upit je parametrizovan
    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Pogrešan email ili lozinka.")
    logger.info(f"🔑 Korisnik ulogovan: {email}")
    return AuthResponse(token=create_jwt(email), email=email, plan=row["plan"])


@router.get("/auth/me")
async def auth_me(request: Request):
    """Provjera tokena — vraća info o korisniku."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token nije proslijeđen.")
    token = auth_header.split(" ", 1)[1]
    payload = decode_jwt(token)
    email = payload["sub"]
    with db_ctx() as (conn, cf):
        row = db_exec(conn, cf, f"SELECT email, plan, created_at FROM users WHERE email = {ph()}", (email,)).fetchone()  # nosec B608 — ph() je placeholder, upit je parametrizovan
    if not row:
        raise HTTPException(status_code=404, detail="Korisnik ne postoji.")
    return {"email": row["email"], "plan": row["plan"], "created_at": row["created_at"]}
