"""
backend/app/api/search.py — Vektorska pretraga, AI odgovori i manualni ingest.
"""

import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.schemas import (
    AIAnswerRequest,
    AIAnswerResponse,
    SearchRequest,
    SearchResponse,
)
from backend.app.core.security import get_current_user
from backend.app.services import ai as ai_services

logger = logging.getLogger("eu_grants_api")

router = APIRouter()


def _grant_quality_score(query: str, metadata: dict, document: str) -> int:
    """Small deterministic reranker for safer grant search results."""
    query_l = (query or "").lower()
    title = str(metadata.get("title", "") or "").lower()
    category = str(metadata.get("category", "") or "").lower()
    status = str(metadata.get("status", "") or "").lower()
    relevance = str(metadata.get("relevance", "") or "").lower()
    url = str(metadata.get("url", "") or "").strip().lower()
    doc_l = str(document or "").lower()

    combined = f"{title} {category} {doc_l}"
    score = 0

    status_weights = {
        "rolling": 30,
        "u_pripremi": 20,
        "open": 25,
        "otvoren": 25,
        "zatvoren": -10,
        "closed": -10,
        "neprovjereno": -25,
        "neizvjesno": -25,
        "needs_review": -35,
    }
    score += status_weights.get(status, -5 if not status else 0)

    relevance_weights = {
        "high": 15,
        "medium": 5,
        "low": -10,
    }
    score += relevance_weights.get(relevance, 0)

    if not url:
        score -= 40
    elif url in {
        "https://www.vijeceministara.gov.ba/",
        "https://vijeceministara.gov.ba/",
        "https://www.interreg.eu/",
        "https://interreg.eu/",
    }:
        score -= 15

    if "innovate bosnia" in combined or "fipa" in combined:
        score -= 35

    agriculture_query_terms = {
        "poljoprivred",
        "rural",
        "stocar",
        "vocar",
        "farma",
        "pcel",
        "agri",
        "fmpvs",
    }
    agriculture_doc_terms = {
        "poljoprivred",
        "rural",
        "stocar",
        "vocar",
        "farma",
        "pcel",
        "eu4agri",
        "fmpvs",
    }

    digital_query_terms = {
        "digital",
        "digitaliz",
        "msp",
        "sme",
        "startup",
        "start-up",
        "zdk",
        "tesanj",
        "obrt",
    }
    digital_doc_terms = {
        "digital",
        "digitaliz",
        "msp",
        "sme",
        "startup",
        "zdk",
        "tesanj",
        "zeda",
        "fmrpo",
        "konkurentnost",
        "obrt",
    }

    if any(term in query_l for term in agriculture_query_terms):
        if any(term in combined for term in agriculture_doc_terms):
            score += 35
        if "it sektor" in combined or "fipa" in combined:
            score -= 45

    if any(term in query_l for term in digital_query_terms):
        if any(term in combined for term in digital_doc_terms):
            score += 30

    # Additional trust / quality tuning
    if "neprovjereno" in doc_l:
        score -= 50

    if "neizvjesno" in doc_l:
        score -= 35

    if "agregator" in doc_l:
        score -= 10

    if "fmpvs" in combined:
        score += 25

    if "eu4agri" in combined:
        score += 20

    if "zeda" in combined:
        score += 15

    if "fmrpo" in combined:
        score += 15

    return score


def _rerank_search_results(query: str, documents: list, metadatas: list, limit: int):
    """Rerank Chroma results while preserving response-compatible shapes."""
    items = []
    for index, document in enumerate(documents):
        metadata = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
        quality_score = _grant_quality_score(query, metadata, document)
        items.append((quality_score, index, document, metadata))

    items.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    selected = items[:limit]

    reranked_documents = [item[2] for item in selected]
    reranked_metadatas = [item[3] for item in selected]
    return reranked_documents, reranked_metadatas



@router.post("/ingest")
async def manual_ingest(current_user: str = Depends(get_current_user)):
    """Manualni re-ingest grantova u ChromaDB bez restarta servera."""
    if not ai_services.embedding_client or not ai_services.chroma_client:
        raise HTTPException(status_code=503, detail="AI sistem nije spreman.")
    try:
        ai_services.load_grants_cache()
        await ai_services.auto_ingest_grants()
        return {
            "status": "ok",
            "triggered_by": current_user,
            "grants_cache_count": len(ai_services._grants_cache),
            "grants_in_db": ai_services.chroma_client.collection.count(),
        }
    except Exception as e:
        logger.error(f"❌ Manualni ingest greška: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
async def search_endpoint(request: SearchRequest, current_user: str = Depends(get_current_user)):
    """
    Glavni endpoint za pretragu.
    1. Prima tekst.
    2. Pretvara ga u vektor (Gemini).
    3. Traži u bazi (Chroma).
    4. Vraća rezultate.
    """
    start_time = time.time()
    req_id = str(uuid.uuid4())
    logger.info(f"🔍 [ID: {req_id}] Primljen upit: '{request.query}'")

    if not ai_services.embedding_client or not ai_services.chroma_client:
        raise HTTPException(status_code=503, detail="Sistem se još inicijalizuje, pokušajte za 10 sekundi.")

    try:
        # KORAK 1: Embedding Upita
        query_vectors = ai_services.embedding_client.generate_embeddings([request.query])

        if not query_vectors:
            logger.error(f"❌ [ID: {req_id}] Embedding nije uspio.")
            raise HTTPException(status_code=500, detail="Greška pri generisanju AI vektora.")

        # KORAK 2: Pretraga u Bazi
        # Fetch a wider candidate set, then apply deterministic safety reranking.
        doc_count = ai_services.chroma_client.collection.count()
        requested_n = max(request.n_results, 1)
        candidate_n = min(max(requested_n * 3, requested_n), max(doc_count, 1))
        search_results = ai_services.chroma_client.query(
            query_embeddings=query_vectors,
            n_results=candidate_n
        )

        raw_documents = search_results.get("documents", [[]])[0] if search_results else []
        raw_metadatas = search_results.get("metadatas", [[]])[0] if search_results else []

        flat_results, flat_metadatas = _rerank_search_results(
            request.query,
            raw_documents,
            raw_metadatas,
            requested_n,
        )

        # Frontend compatibility: JS expects a list of strings in "results".
        documents = [flat_results]
        metadatas = [flat_metadatas]

        duration = time.time() - start_time
        logger.info(f"✅ [ID: {req_id}] Pretraga završena za {duration:.2f}s. Nađeno {len(flat_results)} rezultata.")

        return SearchResponse(
            results=flat_results,
            documents=documents,
            metadatas=metadatas,
            request_id=req_id,
            processing_time=duration
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔥 [ID: {req_id}] Neočekivana greška: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai-answer", response_model=AIAnswerResponse)
async def ai_answer_endpoint(request: AIAnswerRequest, current_user: str = Depends(get_current_user)):
    """
    AI odgovor koji kombinuje RAG pretragu + Gemini generaciju (gemini-2.5-flash).
    Vraća strukturirani odgovor na bosanskom ili engleskom jeziku.
    """
    start_time = time.time()
    req_id = str(uuid.uuid4())
    logger.info(f"🤖 [ID: {req_id}] AI upit: '{request.query}' | lang={request.language}")

    if not ai_services.embedding_client or not ai_services.chroma_client or not ai_services.genai_client:
        raise HTTPException(status_code=503, detail="Sistem se još inicijalizuje, pokušajte za 10 sekundi.")

    try:
        # Pretraga relevantnih grantova
        query_vectors = ai_services.embedding_client.generate_embeddings([request.query])
        if not query_vectors:
            raise HTTPException(status_code=500, detail="Greška pri generisanju AI vektora.")

        doc_count = ai_services.chroma_client.collection.count()
        candidate_n = min(12, max(doc_count, 1))
        search_results = ai_services.chroma_client.query(
            query_embeddings=query_vectors,
            n_results=candidate_n
        )

        raw_metadatas = search_results.get("metadatas", [[]])[0]
        raw_documents = search_results.get("documents", [[]])[0]
        documents, metadatas = _rerank_search_results(
            request.query,
            raw_documents,
            raw_metadatas,
            5,
        )

        # Kontekst za AI
        context_parts = []
        sources = []
        for meta, doc in zip(metadatas, documents):
            title = meta.get("title", "Nepoznat grant")
            category = meta.get("category", "")
            budget = meta.get("budget", "N/A")
            deadline = meta.get("deadline", "N/A")
            url = meta.get("url", "")
            context_parts.append(
                f"• {title} ({category})\n"
                f"  Budžet: {budget} | Rok: {deadline}\n"
                f"  Opis: {doc[:250]}"
            )
            if url:
                sources.append({"title": title, "category": category, "url": url})

        context = "\n\n".join(context_parts) if context_parts else "Nema pronađenih grantova."

        lang_instruction = (
            "Odgovaraj ISKLJUČIVO na bosanskom jeziku."
            if request.language == "bs"
            else "Answer in English."
        )

        prompt = f"""Ti si FinAssistBH — ekspert za EU fondove i grantove u Bosni i Hercegovini.
Specijaliziran si za: Federalne pozive (FMRPO, FMPVS, FZZZ), kantonalne pozive ZDK/Tešanj,
EU programe (EU4Agri, EU4CAET, Horizont Evropa), i lokalne poticaje.

{lang_instruction}

DOSTUPNI GRANTOVI IZ BAZE:
{context}

KORISNIČKO PITANJE:
{request.query}

INSTRUKCIJE:
- Koristi informacije iz konteksta iznad
- Navedi konkretne iznose, rokove i izvore kad su dostupni
- Ako pitanje nije o grantovima, ljubazno usmjeri korisnika
- Budi konkretan, koristan i precizan
- Završi s preporukom sljedećeg koraka (npr. koji URL posjetiti)
"""

        answer = ai_services.genai_client.generate(prompt)

        if not answer:
            answer = "Nisam pronašao odgovor. Pokušajte precizirati upit ili kontaktirajte FMRPO na javnipozivi.fmrpo.gov.ba."

        duration = time.time() - start_time
        logger.info(f"✅ [ID: {req_id}] AI odgovor generisan za {duration:.2f}s ({len(answer)} znakova)")

        return AIAnswerResponse(
            answer=answer,
            sources=sources[:5],
            request_id=req_id,
            processing_time=duration,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔥 [ID: {req_id}] AI greška: {e}")
        raise HTTPException(status_code=500, detail=str(e))
