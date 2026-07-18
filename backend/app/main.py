"""
backend/app/main.py — FastAPI entry point (orkestracija).

Pokretanje iz root-a repozitorija:
    uvicorn backend.app.main:app --reload
"""

import logging
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.api import auth, grants, search, system, webhooks
from backend.app.core import config, rate_limit
from backend.app.core.database import init_user_db
from backend.app.services import ai as ai_services

# --- KONFIGURACIJA LOGOVANJA ---
# Windows fix: cp1252 ne podržava emoji — force UTF-8 na stdout/stderr
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("eu_grants_api")


app = FastAPI(
    title="FinAssistBH AI Platform API",
    description="Enterprise-grade AI API za EU fondove u BiH (Gemini embeddings + RAG).",
    version="v2.1.0-enterprise"
)


# --- SECURITY MIDDLEWARE LAYER ---
class ProductionSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response


app.add_middleware(ProductionSecurityMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Globalni rate limiter po IP adresi."""
    # Preskači health check da Render ne dobije 429
    if request.url.path in ("/health", "/"):
        return await call_next(request)
    ip = request.client.host if request.client else "unknown"
    if not rate_limit._check_rate_limit(ip):
        return JSONResponse(
            status_code=429,
            content={"detail": (
                f"Previše zahtjeva. Maksimum {rate_limit.RATE_LIMIT_REQUESTS} "
                f"zahtjeva/{rate_limit.RATE_LIMIT_WINDOW}s."
            )}
        )
    return await call_next(request)


# --- RUTE ---
app.include_router(system.router)
app.include_router(search.router)
app.include_router(grants.router)
app.include_router(auth.router)
app.include_router(webhooks.router)


# --- INICIJALIZACIJA PRI STARTU ---
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Podižem FinAssistBH AI Sistem...")

    import os
    # JWT_SECRET se reset-uje pri svakom restartu ako nije u env-u
    # → svi korisnici ostanu bez sesije nakon deploya
    if not os.getenv("JWT_SECRET"):
        logger.warning(
            "⚠️  JWT_SECRET nije postavljen! Korisnici će biti odjavljeni "
            "na svakom Render restartu. Dodaj JWT_SECRET u Render Environment."
        )

    # users.db je ephemeral na Render free tier — podaci se brišu
    if not os.getenv("DATABASE_URL"):
        logger.warning(
            "⚠️  Korisnici se čuvaju u SQLite (users.db). "
            "Na Render free tier disk se briše pri restartu — razmisli o Supabase/PostgreSQL."
        )

    try:
        init_user_db()
        logger.info("✅ Baza korisnika inicijalizovana.")
    except Exception as e:
        logger.warning(
            f"⚠️  DB konekcija nije uspjela ({e}) — prelazim na SQLite fallback."
        )
        config.use_sqlite_fallback()
        init_user_db()
        logger.info("✅ SQLite fallback baza korisnika inicijalizovana.")

    ai_services.load_grants_cache()

    try:
        ai_services.init_ai_clients()
        await ai_services.auto_ingest_grants()
    except Exception as e:
        logger.critical(f"❌ Kritična greška pri startu: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
