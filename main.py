import os
import logging
import time
import uuid
import json
import sqlite3
import hashlib
import secrets
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
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

# --- Rate Limiter (in-memory, per-IP) ---
_rate_limit_store: Dict[str, List[float]] = defaultdict(list)
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))  # max zahtjeva
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))       # u sekundi

def _check_rate_limit(ip: str) -> bool:
    """Vraća True ako IP nije prešao limit. Čisti stare upise automatski."""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    calls = _rate_limit_store[ip]
    # Ukloni zahtjeve starije od window-a
    _rate_limit_store[ip] = [t for t in calls if t > window_start]
    if len(_rate_limit_store[ip]) >= RATE_LIMIT_REQUESTS:
        return False
    _rate_limit_store[ip].append(now)
    return True

# Cache grantova (učita se jednom pri startu)
_grants_cache: List[Dict] = []
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


# --- 2a. SQLite baza korisnika ---

PLAN_LIMITS: Dict[str, int] = {
    "free":       10,   # upita/dan
    "premium":    -1,   # neograničeno
    "enterprise": -1,   # neograničeno
}
GUEST_LIMIT = 3   # informativno (enforcement je na frontendu)


def init_user_db():
    """Kreira tabele korisnika i dnevnih kvota ako ne postoje."""
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
        db.execute("""
            CREATE TABLE IF NOT EXISTS query_counts (
                email TEXT NOT NULL,
                date  TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (email, date)
            )
        """)
        db.commit()


def _get_daily_count(email: str) -> int:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute(
            "SELECT count FROM query_counts WHERE email=? AND date=?", (email, today)
        ).fetchone()
    return row[0] if row else 0


def _increment_daily_count(email: str) -> int:
    """Uveća dnevni broj upita i vraća novi count."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT INTO query_counts (email, date, count) VALUES (?,?,1) "
            "ON CONFLICT(email, date) DO UPDATE SET count = count + 1",
            (email, today)
        )
        db.commit()
        row = db.execute(
            "SELECT count FROM query_counts WHERE email=? AND date=?", (email, today)
        ).fetchone()
    return row[0] if row else 1


def _get_user_plan(email: str) -> str:
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute("SELECT plan FROM users WHERE email=?", (email,)).fetchone()
    return row[0] if row else "free"


def _decode_token_optional(request: Request) -> Optional[str]:
    """Čita JWT iz Authorization headera, vraća email ili None (ne baca grešku)."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


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

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Neispravan format email adrese.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Lozinka mora imati minimalno 6 karaktera.")
        return v

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

class QuotaInfo(BaseModel):
    plan: str
    used: Optional[int] = None
    limit: Optional[int] = None   # -1 = neograničeno
    remaining: Optional[int] = None

class SearchResponse(BaseModel):
    """
    Format odgovora koji Frontend očekuje.
    """
    results: List[str]
    documents: List[List[str]]
    metadatas: List[List[Dict[str, Any]]]
    request_id: str
    processing_time: float
    quota: Optional[QuotaInfo] = None   # uključeno ako je korisnik prijavljen

class AIAnswerRequest(BaseModel):
    """Zahtjev za AI odgovor (RAG + Gemini generacija)."""
    query: str = Field(..., min_length=3, max_length=500)
    language: str = Field(default="bs", description="Jezik odgovora: 'bs' (bosanski) ili 'en' (engleski)")

class AIAnswerResponse(BaseModel):
    """AI-generirani odgovor s izvorima."""
    answer: str
    sources: List[Dict[str, str]]  # [{title, category, url}]
    request_id: str
    processing_time: float

# --- 4. INICIJALIZACIJA PRI STARTU ---

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Globalni rate limiter po IP adresi."""
    # Preskači health check da Render ne dobije 429
    if request.url.path in ("/health", "/"):
        return await call_next(request)
    ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(ip):
        return JSONResponse(
            status_code=429,
            content={"detail": f"Previše zahtjeva. Maksimum {RATE_LIMIT_REQUESTS} zahtjeva/{RATE_LIMIT_WINDOW}s."}
        )
    return await call_next(request)


@app.on_event("startup")
async def startup_event():
    global embedding_client, chroma_client, _grants_cache
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

    # Učitaj grants.json u memorijski cache
    grants_path = os.path.join(os.path.dirname(__file__), "data", "grants.json")
    if os.path.exists(grants_path):
        with open(grants_path, "r", encoding="utf-8") as f:
            _grants_cache = json.load(f)
        logger.info(f"✅ Grants cache učitan: {len(_grants_cache)} grantova.")
    else:
        logger.warning("⚠️ data/grants.json nije pronađen — grants cache prazan.")

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
    """System Health Check za Render — prošireni status."""
    grant_count = 0
    chroma_docs = 0
    try:
        if chroma_client:
            chroma_docs = chroma_client.collection.count()
    except Exception:
        pass

    today = datetime.utcnow().date()
    urgent = [
        g for g in _grants_cache
        if g.get("deadline") and g["deadline"] != "N/A"
        and (datetime.strptime(g["deadline"], "%Y-%m-%d").date() - today).days <= 30
        and (datetime.strptime(g["deadline"], "%Y-%m-%d").date() - today).days >= 0
    ] if _grants_cache else []

    return {
        "status": "healthy",
        "version": "v2.2.0",
        "database": "connected" if chroma_client else "disconnected",
        "ai_engine": "ready" if embedding_client else "offline",
        "grants_total": len(_grants_cache),
        "grants_in_vector_db": chroma_docs,
        "grants_urgent_30d": len(urgent),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

@app.post("/search", response_model=SearchResponse)
async def search_endpoint(http_request: Request, request: SearchRequest):
    """
    Glavni endpoint za pretragu.
    - Gost (bez tokena): pretraga radi, kvota=None (frontend broji)
    - Free korisnik: 10 upita/dan, backend broji i blokira
    - Premium/Enterprise: neograničeno
    """
    start_time = time.time()
    req_id = str(uuid.uuid4())
    logger.info(f"🔍 [ID: {req_id}] Primljen upit: '{request.query}'")

    if not embedding_client or not chroma_client:
        raise HTTPException(status_code=503, detail="Sistem se još inicijalizuje, pokušajte za 10 sekundi.")

    # --- Kvota provjera za prijavljene korisnike ---
    quota_info: Optional[QuotaInfo] = None
    email = _decode_token_optional(http_request)

    if email:
        plan = _get_user_plan(email)
        limit = PLAN_LIMITS.get(plan, 10)

        if limit != -1:  # -1 = neograničeno (premium/enterprise)
            used = _get_daily_count(email)
            if used >= limit:
                remaining_secs = (
                    datetime.utcnow().replace(hour=23, minute=59, second=59) - datetime.utcnow()
                ).seconds
                raise HTTPException(
                    status_code=429,
                    detail={
                        "code": "QUOTA_EXCEEDED",
                        "plan": plan,
                        "used": used,
                        "limit": limit,
                        "reset_in_seconds": remaining_secs,
                        "message": f"Dnevni limit od {limit} upita je dostignut. Reset u ponoć.",
                    }
                )
            new_count = _increment_daily_count(email)
            quota_info = QuotaInfo(
                plan=plan, used=new_count, limit=limit, remaining=max(0, limit - new_count)
            )
            logger.info(f"📊 [{email}] plan={plan} | used={new_count}/{limit}")
        else:
            quota_info = QuotaInfo(plan=plan, used=None, limit=-1, remaining=None)

    try:
        query_vectors = embedding_client.generate_embeddings([request.query])
        if not query_vectors:
            raise HTTPException(status_code=500, detail="Greška pri generisanju AI vektora.")

        doc_count = chroma_client.collection.count()
        safe_n = min(request.n_results, max(doc_count, 1))
        search_results = chroma_client.query(
            query_embeddings=query_vectors,
            n_results=safe_n
        )

        documents = search_results['documents'] if search_results else []
        metadatas = search_results['metadatas'] if search_results else []
        flat_results = documents[0] if documents else []

        duration = time.time() - start_time
        logger.info(f"✅ [ID: {req_id}] {len(flat_results)} rezultata za {duration:.2f}s")

        return SearchResponse(
            results=flat_results,
            documents=documents,
            metadatas=metadatas,
            request_id=req_id,
            processing_time=duration,
            quota=quota_info,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"🔥 [ID: {req_id}] Neočekivana greška: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- 5b. AI ANSWER ENDPOINT (RAG + Gemini generacija) ---

@app.post("/ai-answer", response_model=AIAnswerResponse)
async def ai_answer_endpoint(request: AIAnswerRequest):
    """
    AI odgovor koji kombinuje RAG pretragu + Gemini 2.0 Flash generaciju.
    Vraća strukturirani odgovor na bosanskom ili engleskom jeziku.
    """
    start_time = time.time()
    req_id = str(uuid.uuid4())
    logger.info(f"🤖 [ID: {req_id}] AI upit: '{request.query}' | lang={request.language}")

    if not embedding_client or not chroma_client:
        raise HTTPException(status_code=503, detail="Sistem se još inicijalizuje, pokušajte za 10 sekundi.")

    try:
        from agent.agent import EUFundsAgent
    except ImportError as e:
        logger.error(f"❌ [ID: {req_id}] Agent import greška: {e}")
        raise HTTPException(status_code=500, detail="AI agent nije dostupan.")

    try:
        # Pretraga relevantnih grantova
        query_vectors = embedding_client.generate_embeddings([request.query])
        if not query_vectors:
            raise HTTPException(status_code=500, detail="Greška pri generisanju AI vektora.")

        doc_count = chroma_client.collection.count()
        safe_n = min(5, max(doc_count, 1))
        search_results = chroma_client.query(
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

        from agent.genai_client import GenAIClient
        genai_client = GenAIClient()
        answer = genai_client.generate(prompt)

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


# --- 5c. GRANTS REST ENDPOINTI ---

LOCAL_CATEGORIES = {"Kantonalni (ZDK)", "Lokalni", "ZDK", "Tešanj", "ZEDA"}
LOCAL_KEYWORDS = ["zdk", "tešanj", "tesanj", "zeda", "zenica", "kanton", "federalni zavod za zapošljavanje"]

@app.get("/grants")
def list_grants(
    category: Optional[str] = None,
    relevance: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    """
    Vraća listu svih dostupnih grantova iz baze.
    Parametri: category, relevance (High/Medium/Low), page, page_size.
    """
    filtered = _grants_cache

    if category:
        filtered = [g for g in filtered if category.lower() in g.get("category", "").lower()]
    if relevance:
        filtered = [g for g in filtered if g.get("relevance", "").lower() == relevance.lower()]

    total = len(filtered)
    start = (page - 1) * page_size
    paginated = filtered[start: start + page_size]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
        "grants": paginated,
    }


@app.get("/grants/local")
def list_local_grants():
    """
    Vraća grantove relevantne za ZDK kanton i Tešanj (Tier 1 prioritet).
    Uključuje kantonalne i federalne pozive koji pokrivaju ZDK područje.
    """
    local = []
    for g in _grants_cache:
        cat = g.get("category", "").lower()
        title = g.get("title", "").lower()
        desc = g.get("description", "").lower()
        combined = f"{cat} {title} {desc}"
        if any(kw in combined for kw in LOCAL_KEYWORDS) or g.get("category") in LOCAL_CATEGORIES:
            local.append(g)

    return {
        "region": "ZDK — Zeničko-dobojski kanton / Tešanj",
        "total": len(local),
        "note": "Ovi grantovi su direktno relevantni za poduzetnike iz ZDK kantona.",
        "grants": local,
    }


@app.get("/grants/urgent")
def list_urgent_grants(days: int = 30):
    """
    Vraća grantove čiji rok ističe unutar zadanog broja dana (default: 30).
    """
    today = datetime.utcnow().date()
    urgent = []
    for g in _grants_cache:
        deadline_str = g.get("deadline", "")
        if not deadline_str or deadline_str in ("N/A", "Varijabilno", ""):
            continue
        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            days_left = (deadline - today).days
            if 0 <= days_left <= days:
                urgent.append({**g, "days_left": days_left})
        except ValueError:
            continue

    urgent.sort(key=lambda x: x["days_left"])

    return {
        "window_days": days,
        "total": len(urgent),
        "as_of": today.isoformat(),
        "grants": urgent,
    }


# --- 6. AUTH ENDPOINTI ---

@app.post("/auth/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    """Registracija novog korisnika. Validacija emaila i lozinke je u Pydantic modelu."""
    email = req.email  # već normalizovan u validator-u
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


@app.get("/auth/quota")
async def auth_quota(request: Request):
    """
    Vraća dnevnu kvotu za prijavljenog korisnika.
    Frontend koristi ovaj endpoint da prikaže badge (npr. 'Free: 7/10').
    """
    email = _decode_token_optional(request)
    if not email:
        raise HTTPException(status_code=401, detail="Token nije proslijeđen.")
    plan = _get_user_plan(email)
    limit = PLAN_LIMITS.get(plan, 10)
    used = _get_daily_count(email) if limit != -1 else None
    remaining = max(0, limit - used) if (limit != -1 and used is not None) else None
    midnight = datetime.utcnow().replace(hour=0, minute=0, second=0).replace(
        day=(datetime.utcnow().day + 1) if datetime.utcnow().hour >= 0 else datetime.utcnow().day
    )
    return {
        "email": email,
        "plan": plan,
        "used_today": used,
        "limit": limit,            # -1 = neograničeno
        "remaining": remaining,
        "guest_limit": GUEST_LIMIT,
        "reset_at": midnight.strftime("%Y-%m-%dT00:00:00Z"),
    }


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
