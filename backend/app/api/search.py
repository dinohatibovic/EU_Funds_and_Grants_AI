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


@router.post("/ingest")
async def manual_ingest(current_user: str = Depends(get_current_user)):
    """Manualni re-ingest grantova u ChromaDB bez restarta servera."""
    if not ai_services.embedding_client or not ai_services.chroma_client:
        raise HTTPException(status_code=503, detail="AI sistem nije spreman.")
    try:
        await ai_services.auto_ingest_grants()
        return {
            "status": "ok",
            "triggered_by": current_user,
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
        # ChromaDB baca grešku ako n_results > broj dokumenata u kolekciji
        doc_count = ai_services.chroma_client.collection.count()
        safe_n = min(request.n_results, max(doc_count, 1))
        search_results = ai_services.chroma_client.query(
            query_embeddings=query_vectors,
            n_results=safe_n
        )

        # ChromaDB vraća liste unutar listi, pa ih moramo "otpakovati"
        documents = search_results['documents'] if search_results else []
        metadatas = search_results['metadatas'] if search_results else []

        # Za frontend kompatibilnost (JS očekuje listu stringova u 'results')
        flat_results = documents[0] if documents else []

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
    AI odgovor koji kombinuje RAG pretragu + Gemini 2.0 Flash generaciju.
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
        safe_n = min(5, max(doc_count, 1))
        search_results = ai_services.chroma_client.query(
            query_embeddings=query_vectors,
            n_results=safe_n
        )

        metadatas = search_results.get("metadatas", [[]])[0]
        documents = search_results.get("documents", [[]])[0]

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
