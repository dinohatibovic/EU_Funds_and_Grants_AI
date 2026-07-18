"""
backend/app/api/system.py — Status i health check endpointi.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from backend.app.core import config
from backend.app.services import ai as ai_services

router = APIRouter()


@router.get("/")
def root():
    return {
        "message": "FinAssistBH AI Platform je Online",
        "version": "v2.1.0-enterprise",
        "status": "running"
    }


@router.get("/health")
def health_check():
    """System Health Check za Render — prošireni status."""
    chroma_docs = 0
    try:
        if ai_services.chroma_client:
            chroma_docs = ai_services.chroma_client.collection.count()
    except Exception:
        pass

    grants_cache = ai_services._grants_cache
    today = datetime.now(timezone.utc).date()
    urgent = [
        g for g in grants_cache
        if g.get("deadline") and g["deadline"] != "N/A"
        and (datetime.strptime(g["deadline"], "%Y-%m-%d").date() - today).days <= 30
        and (datetime.strptime(g["deadline"], "%Y-%m-%d").date() - today).days >= 0
    ] if grants_cache else []

    return {
        "status": "healthy",
        "version": "v2.2.0",
        "database": "connected" if ai_services.chroma_client else "disconnected",
        "db_type": "postgresql" if config.DATABASE_URL else "sqlite",
        "ai_engine": "ready" if ai_services.embedding_client else "offline",
        "grants_total": len(grants_cache),
        "grants_in_vector_db": chroma_docs,
        "grants_urgent_30d": len(urgent),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
