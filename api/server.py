"""
FASTAPI SERVER - EU Funds and Grants AI
========================================
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag.pipeline import RAGPipeline
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="EU Funds and Grants AI",
    description="AI-powered search for EU and national grants",
    version="1.0.0"
)

# ✅ DODAJ CORS MIDDLEWARE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG pipeline
try:
    pipeline = RAGPipeline()
    logger.info("✅ RAG Pipeline loaded")
except Exception as e:
    logger.error(f"❌ Error loading pipeline: {e}")
    pipeline = None

# Models
class SearchRequest(BaseModel):
    query: str
    n_results: int = 5

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
        raise HTTPException(status_code=500, detail="Pipeline not initialized")
    
    try:
        results = pipeline.search(request.query, request.n_results)
        return {
            "query": request.query,
            "results_count": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"❌ Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def stats():
    """Get pipeline statistics."""
    if not pipeline:
        raise HTTPException(status_code=500, detail="Pipeline not initialized")
    
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
