"""
backend/app/services/ai.py — Servisni sloj koji spaja backend sa AI slojem (ai_core).

Drži globalne klijente (embeddings, ChromaDB, Gemini) i grants cache.
Ostali moduli MORAJU pristupati preko modula (services.ai.embedding_client),
ne preko from-importa, jer se klijenti inicijalizuju tek na startupu.
"""

import json
import logging
from typing import Dict, List

from backend.app.core import config

logger = logging.getLogger("eu_grants_api")

# --- Globalni klijenti (inicijalizuju se u init_ai_clients na startupu) ---
embedding_client = None
chroma_client = None
genai_client = None

# Cache grantova (učita se jednom pri startu)
_grants_cache: List[Dict] = []

_EMBED_BATCH_SIZE = 10  # Gemini ima rate limite — šaljemo u manjim grupama


def load_grants_cache() -> None:
    """Učitava data/grants.json u memorijski cache."""
    global _grants_cache
    if config.GRANTS_FILE.exists():
        with open(config.GRANTS_FILE, "r", encoding="utf-8") as f:
            _grants_cache = json.load(f)
        logger.info(f"✅ Grants cache učitan: {len(_grants_cache)} grantova.")
    else:
        logger.warning("⚠️ data/grants.json nije pronađen — grants cache prazan.")


def init_ai_clients() -> None:
    """Inicijalizuje Gemini embedding, ChromaDB i GenAI klijente."""
    global embedding_client, chroma_client, genai_client
    from ai_core.agent.genai_client import GenAIClient
    from ai_core.embeddings.embedding_client import EmbeddingClient
    from ai_core.vector_store.chroma_client import ChromaDBClient

    embedding_client = EmbeddingClient()
    chroma_client = ChromaDBClient()
    genai_client = GenAIClient()
    logger.info("✅ Klijenti za Gemini AI i ChromaDB su spremni.")


async def auto_ingest_grants() -> None:
    """
    Auto-ingestira grants.json u ChromaDB (full refresh).
    Render briše disk pri svakom restartu — ovo osigurava da podaci uvijek budu tu.
    """
    if not config.GRANTS_FILE.exists():
        logger.warning("⚠️ data/grants.json nije pronađen — preskačem auto-ingestion.")
        return

    with open(config.GRANTS_FILE, "r", encoding="utf-8") as f:
        grants = json.load(f)

    collection = chroma_client.collection

    # Dohvati sve postojeće ID-eve i obriši ih (full refresh)
    try:
        existing_ids = collection.get()["ids"]
    except Exception:
        existing_ids = []

    if existing_ids:
        collection.delete(ids=existing_ids)
        logger.info(f"🗑️ Obrisano {len(existing_ids)} postojećih dokumenata iz ChromaDB.")

    logger.info(f"📥 Auto-ingestion: ingestiram svih {len(grants)} grantova iz grants.json...")

    texts = [
        f"{g['title']}. {g.get('description', '')} Kategorija: {g.get('category', '')}. "
        f"Budžet: {g.get('budget', '')}. Rok: {g.get('deadline', '')}."
        for g in grants
    ]

    # Slanje svih tekstova odjednom može srušiti Gemini rate limit
    # → šaljemo u batchovima od _EMBED_BATCH_SIZE
    all_embeddings: list = []
    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        chunk = texts[i: i + _EMBED_BATCH_SIZE]
        batch_emb = embedding_client.generate_embeddings(chunk)
        if not batch_emb:
            logger.error(f"❌ Embedding batch {i // _EMBED_BATCH_SIZE + 1} neuspješan — prekidam ingestion.")
            return
        all_embeddings.extend(batch_emb)

    if len(all_embeddings) != len(grants):
        logger.error("❌ Broj embeddinga ne odgovara broju grantova — prekidam.")
        return

    ids = [g["id"] for g in grants]
    metadatas = [
        {
            "title": g["title"],
            "category": g.get("category", ""),
            "budget": g.get("budget", ""),
            "deadline": str(g.get("deadline", "")) if g.get("deadline") is not None else "",
            "url": g.get("url", ""),
            "relevance": g.get("relevance", ""),
        }
        for g in grants
    ]

    collection.add(ids=ids, embeddings=all_embeddings, metadatas=metadatas, documents=texts)
    logger.info(f"✅ Auto-ingestion završen — {len(grants)} grantova dodano u ChromaDB.")
