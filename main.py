import os
import logging
import time
import uuid
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Uvozimo tvoje popravljene module
from embeddings.embedding_client import EmbeddingClient
from vector_db.chroma_client import ChromaDBClient

# --- 1. KONFIGURACIJA LOGOVANJA (Enterprise Level) ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("eu_grants_api")

# --- 2. INICIJALIZACIJA SISTEMA ---
# Ovo se pokreće samo jednom kad se server upali
logger.info("🚀 Podižem EU Funds AI Sistem...")

try:
    # Inicijalizujemo klijente koje si popravio
    embedding_client = EmbeddingClient()
    chroma_client = ChromaDBClient()
    logger.info("✅ Klijenti za AI i Bazu su spremni.")
except Exception as e:
    logger.critical(f"❌ Kritična greška pri startu: {e}")
    # Ne dižemo exception ovdje da bi se server ipak upalio, ali logujemo grešku

app = FastAPI(
    title="EU Funds & Grants AI",
    description="Napredni AI sistem za pretragu grantova u BiH koristeći Google Gemini 3072-dim embeddinge.",
    version="2.1.0-enterprise"
)

# CORS (Dozvole za Frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # U produkciji ovdje staviš svoj GitHub Pages URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. DOMENSKI MODELI (Ono što si tražio iz JSON-a) ---

class SearchRequest(BaseModel):
    """
    Model zahtjeva koji stiže sa Frontenda.
    """
    query: str = Field(..., min_length=3, description="Korisnički upit, npr. 'startups in BiH'")
    n_results: int = Field(default=5, ge=1, le=20, description="Broj rezultata za vratiti")

class GrantResult(BaseModel):
    """
    Struktura jednog rezultata pretrage.
    """
    text: str
    metadata: Dict[str, Any]
    score: Optional[float] = None

class SearchResponse(BaseModel):
    """
    Format odgovora koji Frontend očekuje.
    """
    results: List[str] # Zadržavamo jednostavnu listu stringova za kompatibilnost sa tvojim JS-om
    documents: List[List[str]] # Raw dokumenti iz ChromaDB
    metadatas: List[List[Dict[str, Any]]] # Metapodaci (Izvor, Godina)
    request_id: str
    processing_time: float

# --- 4. API ENDPOINTI ---

@app.get("/")
def root():
    return {"message": "EU Funds and Grants AI API je Online", "version": "2.1.0", "status": "running"}

@app.get("/health")
def health_check():
    """
    Provjerava da li su baza i embedding klijent živi.
    """
    status = {
        "status": "healthy",
        "database": "connected" if chroma_client else "disconnected",
        "ai_engine": "ready" if embedding_client else "offline"
    }
    return status

@app.post("/search", response_model=SearchResponse)
async def search_endpoint(request: SearchRequest):
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

    if not embedding_client or not chroma_client:
        raise HTTPException(status_code=503, detail="Sistem nije u potpunosti inicijalizovan.")

    try:
        # KORAK 1: Embedding Upita
        # Koristimo tvoj embedding_client.py koji sada gađa 'models/gemini-embedding-001'
        query_vectors = embedding_client.generate_embeddings([request.query])
        
        if not query_vectors:
            logger.error(f"❌ [ID: {req_id}] Embedding nije uspio.")
            raise HTTPException(status_code=500, detail="Greška pri generisanju AI vektora.")

        # KORAK 2: Pretraga u Bazi
        # Koristimo tvoj chroma_client.py
        search_results = chroma_client.query(
            query_embeddings=query_vectors,
            n_results=request.n_results
        )

        # ChromaDB vraća čudnu strukturu (liste unutar listi), pa je moramo "otpakovati"
        documents = search_results['documents'] if search_results else []
        metadatas = search_results['metadatas'] if search_results else []
        
        # Za frontend kompatibilnost (tvoj trenutni JS očekuje listu stringova u 'results')
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

    except Exception as e:
        logger.error(f"🔥 [ID: {req_id}] Neočekivana greška: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Ovo služi samo za lokalno testiranje
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
