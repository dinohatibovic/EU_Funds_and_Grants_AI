import os
import logging
import time
import uuid
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import jwt

# Uvozimo tvoje popravljene module (koji sada rade!)
from embeddings.embedding_client import EmbeddingClient
from vector_db.chroma_client import ChromaDBClient

# --- 1. KONFIGURACIJA LOGOVANJA (Enterprise Level) ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("eu_grants_api")

# --- 2. GLOBALNE VARIJABLE ---
embedding_client = None
chroma_client = None

# JWT tajni ključ — postavi JWT_SECRET u Render environment za produkciju
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 30

DB_PATH = os.getenv("DB_PATH", "users.db")


# --- 2a. SQLite baza korisnika ---

def init_user_db():
    """Kreira tabelu korisnika ako ne postoji."""
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                plan TEXT DEFAULT 'free',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()


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
        "exp": datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

app = FastAPI(
    title="FinAssistBH AI Platform API",
    description="Enterprise-grade AI API za EU fondove u BiH (Gemini 3072-dim).",
    version="v2.1.0-enterprise"
)

# CORS — samo dozvoljeni domeni
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:5500",   # VS Code Live Server
    "https://dinohatibovic.github.io",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# --- 3. DOMENSKI MODELI (Pydantic - Iz tvog JSON-a) ---

class RegisterRequest(BaseModel):
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    token: str
    email: str
    plan: str

class SearchRequest(BaseModel):
    """
    Model zahtjeva koji stiže sa Frontenda.
    """
    query: str = Field(..., min_length=3, description="Korisnički upit, npr. 'startups in BiH'")
    n_results: int = Field(default=5, ge=1, le=20, description="Broj rezultata za vratiti")

class SearchResponse(BaseModel):
    """
    Format odgovora koji Frontend očekuje.
    """
    results: List[str] # Jednostavna lista za prikaz na karticama
    documents: List[List[str]] # Raw dokumenti iz ChromaDB (za debug)
    metadatas: List[List[Dict[str, Any]]] # Metapodaci (Izvor, Godina, Kategorija)
    request_id: str
    processing_time: float

# --- 4. INICIJALIZACIJA PRI STARTU ---

@app.on_event("startup")
async def startup_event():
    global embedding_client, chroma_client
    logger.info("🚀 Podižem FinAssistBH AI Sistem...")

    # BUG #3: JWT_SECRET se reset-uje pri svakom restartu ako nije u env-u
    # → svi korisnici ostanu bez sesije nakon deployu
    if not os.getenv("JWT_SECRET"):
        logger.warning(
            "⚠️  JWT_SECRET nije postavljen! Korisnici će biti odjavljeni "
            "na svakom Render restartu. Dodaj JWT_SECRET u Render Environment."
        )

    # BUG #4: users.db je ephemeral na Render free tier — podaci se brišu
    if not os.getenv("DATABASE_URL"):
        logger.warning(
            "⚠️  Korisnici se čuvaju u SQLite (users.db). "
            "Na Render free tier disk se briše pri restartu — razmisli o Supabase/PostgreSQL."
        )

    init_user_db()
    logger.info("✅ SQLite baza korisnika inicijalizovana.")
    try:
        embedding_client = EmbeddingClient()
        chroma_client = ChromaDBClient()
        logger.info("✅ Klijenti za Gemini AI i ChromaDB su spremni.")
        await auto_ingest_grants()
    except Exception as e:
        logger.critical(f"❌ Kritična greška pri startu: {e}")


_EMBED_BATCH_SIZE = 10  # Gemini ima rate limite — šaljemo u manjim grupama


async def auto_ingest_grants():
    """
    Auto-ingestira grants.json u ChromaDB ako je baza prazna ili zastarjela.
    Render briše disk pri svakom restartu — ovo osigurava da podaci uvijek budu tu.
    """
    global embedding_client, chroma_client

    grants_path = os.path.join(os.path.dirname(__file__), "data", "grants.json")
    if not os.path.exists(grants_path):
        logger.warning("⚠️ data/grants.json nije pronađen — preskačem auto-ingestion.")
        return

    with open(grants_path, "r", encoding="utf-8") as f:
        grants = json.load(f)

    collection = chroma_client.collection

    # BUG #7: collection.get(include=[]) može pući na nekim ChromaDB verzijama
    # → koristimo .get() bez include i pristupamo ["ids"] direktno
    try:
        existing_ids = set(collection.get()["ids"])
    except Exception:
        existing_ids = set()

    grant_ids = {g["id"] for g in grants}

    missing = [g for g in grants if g["id"] not in existing_ids]
    if not missing:
        logger.info(f"✅ ChromaDB ima {len(existing_ids)} dokumenata — auto-ingestion preskočen.")
        return

    logger.info(f"📥 Auto-ingestion: {len(missing)} novih grantova u ChromaDB...")

    texts = [
        f"{g['title']}. {g.get('description', '')} Kategorija: {g.get('category', '')}. "
        f"Budžet: {g.get('budget', '')}. Rok: {g.get('deadline', '')}."
        for g in missing
    ]

    # BUG #6: slanje svih tekstova odjednom može srušiti Gemini rate limit
    # → šaljemo u batchovima od _EMBED_BATCH_SIZE
    all_embeddings: list = []
    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        chunk = texts[i : i + _EMBED_BATCH_SIZE]
        batch_emb = embedding_client.generate_embeddings(chunk)
        if not batch_emb:
            logger.error(f"❌ Embedding batch {i//10 + 1} neuspješan — prekidam ingestion.")
            return
        all_embeddings.extend(batch_emb)

    if len(all_embeddings) != len(missing):
        logger.error("❌ Broj embeddinga ne odgovara broju grantova — prekidam.")
        return

    # Ukloni stale dokumente koji više nisu u grants.json
    stale = existing_ids - grant_ids
    if stale:
        collection.delete(ids=list(stale))
        logger.info(f"🗑️ Obrisano {len(stale)} zastarjelih dokumenata.")

    ids = [g["id"] for g in missing]
    metadatas = [
        {
            "title": g["title"],
            "category": g.get("category", ""),
            "budget": g.get("budget", ""),
            "deadline": g.get("deadline", ""),
            "url": g.get("url", ""),
            "relevance": g.get("relevance", ""),
        }
        for g in missing
    ]

    collection.add(ids=ids, embeddings=all_embeddings, metadatas=metadatas, documents=texts)
    logger.info(f"✅ Auto-ingestion završen — {len(missing)} grantova dodano u ChromaDB.")

# --- 5. API ENDPOINTI ---

@app.get("/")
def root():
    return {
        "message": "FinAssistBH AI Platform je Online", 
        "version": "v2.1.0-enterprise", 
        "status": "running"
    }

@app.get("/health")
def health_check():
    """System Health Check za Render."""
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
    2. Pretvara ga u vektor (Gemini 3072-dim).
    3. Traži u bazi (Chroma).
    4. Vraća rezultate.
    """
    start_time = time.time()
    req_id = str(uuid.uuid4())
    logger.info(f"🔍 [ID: {req_id}] Primljen upit: '{request.query}'")

    if not embedding_client or not chroma_client:
        raise HTTPException(status_code=503, detail="Sistem se još inicijalizuje, pokušajte za 10 sekundi.")

    try:
        # KORAK 1: Embedding Upita
        query_vectors = embedding_client.generate_embeddings([request.query])
        
        if not query_vectors:
            logger.error(f"❌ [ID: {req_id}] Embedding nije uspio.")
            raise HTTPException(status_code=500, detail="Greška pri generisanju AI vektora.")

        # KORAK 2: Pretraga u Bazi
        # BUG #2: ChromaDB baca grešku ako n_results > broj dokumenata u kolekciji
        doc_count = chroma_client.collection.count()
        safe_n = min(request.n_results, max(doc_count, 1))
        search_results = chroma_client.query(
            query_embeddings=query_vectors,
            n_results=safe_n
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

# --- 6. AUTH ENDPOINTI ---

@app.post("/auth/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    """Registracija novog korisnika."""
    email = req.email.strip().lower()
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Lozinka mora imati min. 6 karaktera.")
    try:
        with sqlite3.connect(DB_PATH) as db:
            db.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email, hash_password(req.password))
            )
            db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Korisnik s ovim emailom već postoji.")
    logger.info(f"✅ Novi korisnik registrovan: {email}")
    return AuthResponse(token=create_jwt(email), email=email, plan="free")


@app.post("/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    """Prijava korisnika."""
    email = req.email.strip().lower()
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Pogrešan email ili lozinka.")
    logger.info(f"🔑 Korisnik ulogovan: {email}")
    return AuthResponse(token=create_jwt(email), email=email, plan=row["plan"])


@app.get("/auth/me")
async def auth_me(request: Request):
    """Provjera tokena — vraća info o korisniku."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token nije proslijeđen.")
    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token je istekao.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Neispravan token.")
    email = payload["sub"]
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT email, plan, created_at FROM users WHERE email = ?", (email,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Korisnik ne postoji.")
    return {"email": row["email"], "plan": row["plan"], "created_at": row["created_at"]}


# --- 7. STRIPE WEBHOOK (za primanje uplata) ---

STRIPE_SECRET = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """
    Stripe šalje event kad neko plati.
    Ovaj endpoint prima taj event i loguje ga.
    Kad dodaš Supabase, ovdje ćeš upisati pretplatu u bazu.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # Ako Stripe ključevi nisu konfigurisani, loguj i vrati OK
    if not STRIPE_SECRET or not STRIPE_WEBHOOK_SECRET:
        logger.warning("⚠️ Stripe webhook primljen ali ključevi nisu konfigurisani.")
        return {"status": "received", "configured": False}

    try:
        import stripe
        stripe.api_key = STRIPE_SECRET
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception as e:
        logger.error(f"❌ Stripe webhook verifikacija: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # Obradi event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        customer_email = session.get("customer_email", "unknown")
        amount = session.get("amount_total", 0) / 100  # centi → euri
        logger.info(f"💰 NOVA UPLATA: {customer_email} platio €{amount}")

        # TODO: Kad dodaš Supabase, upiši ovdje:
        # supabase.table("subscriptions").insert({
        #     "email": customer_email,
        #     "plan": determine_plan(amount),
        #     "status": "active",
        #     "stripe_session_id": session["id"]
        # }).execute()

    elif event["type"] == "customer.subscription.deleted":
        logger.info(f"🚫 Pretplata otkazana: {event['data']['object'].get('customer', 'unknown')}")

    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
