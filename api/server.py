"""
FASTAPI SERVER - EU Funds and Grants AI
========================================
Sigurna verzija sa CORS lockdown, input validacijom i error handling-om
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from rag.pipeline import RAGPipeline
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="EU Funds and Grants AI",
    description="AI-powered search for EU and national grants",
    version="1.0.0"
)

# ✅ CORS - samo dozvoljeni domeni
# VAŽNO: Kada deployaš, dodaj svoj pravi URL ovdje
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080", 
    "http://127.0.0.1:3000",
    "https://dinohatibovic.github.io",  # tvoj GitHub Pages
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # samo naši domeni, ne "*"
    allow_credentials=False,         # ne trebamo credentials
    allow_methods=["GET", "POST"],   # samo što koristimo
    allow_headers=["Content-Type"],  # samo što koristimo
)

# Initialize RAG pipeline
try:
    pipeline = RAGPipeline()
    logger.info("✅ RAG Pipeline loaded")
except Exception as e:
    logger.error(f"❌ Error loading pipeline: {e}")
    pipeline = None


# ✅ Models sa validacijom
class SearchRequest(BaseModel):
    # Field() dodaje ograničenja — query mora biti 1-500 karaktera
    query: str = Field(..., min_length=1, max_length=500)
    n_results: int = Field(default=5, ge=1, le=20)  # između 1 i 20

    @field_validator('query')
    @classmethod
    def sanitize_query(cls, v):
        # Ukloni višak razmaka i newline karaktere
        # Ovo sprječava neke osnovne injection pokušaje
        cleaned = ' '.join(v.split())
        return cleaned


class SearchResult(BaseModel):
    rank: int
    id: str
    title: str
    category: str
    text: str
    relevance: str


# Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "EU Funds and Grants AI API",
        "version": "1.0.0",
        "status": "running"
    }


@app.post("/search")
async def search(request: SearchRequest):
    """Search for grants."""
    if not pipeline:
        raise HTTPException(
            status_code=503,  # 503 = Service Unavailable, tačnije od 500
            detail="Service temporarily unavailable"  # ne otkrivamo zašto
        )
    try:
        results = pipeline.search(request.query, request.n_results)
        return {
            "query": request.query,
            "results_count": len(results),
            "results": results
        }
    except Exception as e:
        # Logujemo pravu grešku INTERNO (samo mi vidimo)
        logger.error(f"❌ Search error: {e}")
        # Korisniku šaljemo generic poruku (ne otkrivamo detalje)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your request"
        )


@app.get("/stats")
async def stats():
    """Get pipeline statistics."""
    if not pipeline:
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable"
        )
    return pipeline.get_stats()


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "pipeline": "initialized" if pipeline else "not_initialized"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",  # samo lokalno, ne cijela mreža
        port=8000
    )
