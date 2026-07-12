"""
tests/backend_tests/test_agent.py
=================================
Testovi za FinAssistBH AI sistem:
  - EUFundsAgent (RAG + Gemini)
  - FastAPI endpointi (health, search, grants, ai-answer, auth)
  - Rate limiting
  - Email validacija
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# FIXTURE: Test klijent koji mocka vanjske servise
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client(tmp_path_factory):
    """FastAPI TestClient s mockiranim embedding i ChromaDB klijentima."""
    with patch("ai_core.embeddings.embedding_client.genai"), \
         patch("ai_core.vector_store.chroma_client.chromadb"):
        from backend.app import main as app_module
        from backend.app.core import config
        from backend.app.core.database import init_user_db
        from backend.app.services import ai as ai_services

        # Izolovana SQLite baza za testove (ne diraj lokalni users.db)
        config.DB_PATH = str(tmp_path_factory.mktemp("db") / "test_users.db")
        init_user_db()

        # Postavi mock klijente direktno u servisni sloj
        mock_chroma = MagicMock()
        mock_chroma.collection.count.return_value = 10
        mock_chroma.collection.get.return_value = {"ids": []}
        mock_chroma.query.return_value = {
            "documents": [["Test grant o EU fondovima za MSP u ZDK kantonu."]],
            "metadatas": [[{
                "title": "FMRPO MSP Grant 2026",
                "category": "Federalni",
                "budget": "28.000.000 KM",
                "deadline": "2026-04-30",
                "url": "https://javnipozivi.fmrpo.gov.ba/",
                "relevance": "Visoka",
            }]],
        }
        mock_emb = MagicMock()
        mock_emb.generate_embeddings.return_value = [[0.1] * 768]

        ai_services.embedding_client = mock_emb
        ai_services.chroma_client = mock_chroma

        # Učitaj test grants cache
        ai_services._grants_cache = [
            {
                "id": "test_001",
                "title": "Test EU Grant",
                "category": "EU Grant",
                "description": "Testni grant za MSP.",
                "budget": "50.000 KM",
                "deadline": "2026-04-30",
                "relevance": "High",
                "url": "https://example.com/",
            },
            {
                "id": "test_002",
                "title": "ZDK Kantonalni Poziv",
                "category": "Kantonalni (ZDK)",
                "description": "Lokalni ZDK grant za Tešanj.",
                "budget": "10.000 KM",
                "deadline": "2026-05-01",
                "relevance": "High",
                "url": "https://zeda.ba/",
            },
            {
                "id": "test_003",
                "title": "Hitni Grant — Blizu Rok",
                "category": "EU/GIZ",
                "description": "Energetska efikasnost, ističe uskoro.",
                "budget": "99.999 EUR",
                "deadline": "2026-03-20",
                "relevance": "High",
                "url": "https://eu4caet.ba/",
            },
        ]

        yield TestClient(app_module.app)


# ---------------------------------------------------------------------------
# TESTOVI: Osnovni endpointi
# ---------------------------------------------------------------------------

def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "FinAssistBH" in data["message"]
    assert data["status"] == "running"


def test_health_returns_stats(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert "grants_total" in data
    assert "grants_in_vector_db" in data
    assert "grants_urgent_30d" in data
    assert "timestamp" in data


# ---------------------------------------------------------------------------
# TESTOVI: /grants endpointi
# ---------------------------------------------------------------------------

def test_grants_list(client):
    r = client.get("/grants")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "grants" in data
    assert isinstance(data["grants"], list)
    assert data["total"] == 3


def test_grants_filter_by_category(client):
    r = client.get("/grants?category=EU+Grant")
    assert r.status_code == 200
    data = r.json()
    assert all("EU Grant" in g["category"] for g in data["grants"])


def test_grants_filter_by_relevance(client):
    r = client.get("/grants?relevance=High")
    assert r.status_code == 200
    data = r.json()
    assert all(g["relevance"] == "High" for g in data["grants"])


def test_grants_pagination(client):
    r = client.get("/grants?page=1&page_size=2")
    assert r.status_code == 200
    data = r.json()
    assert len(data["grants"]) <= 2
    assert data["page"] == 1


def test_grants_local(client):
    r = client.get("/grants/local")
    assert r.status_code == 200
    data = r.json()
    assert "region" in data
    assert "ZDK" in data["region"]
    assert isinstance(data["grants"], list)
    # ZDK grant mora biti tu
    titles = [g["title"] for g in data["grants"]]
    assert any("ZDK" in t for t in titles)


def test_grants_urgent(client):
    r = client.get("/grants/urgent?days=60")
    assert r.status_code == 200
    data = r.json()
    assert "grants" in data
    assert "window_days" in data
    # Svi moraju imati days_left
    for g in data["grants"]:
        assert "days_left" in g
        assert g["days_left"] >= 0


# ---------------------------------------------------------------------------
# TESTOVI: /search endpoint
# ---------------------------------------------------------------------------

def _auth_headers(client) -> dict:
    """Registruje test korisnika i vraća Authorization header s JWT tokenom."""
    email = "search.tester@example.com"
    password = "sigurna123"
    r = client.post("/auth/register", json={"email": email, "password": password})
    if r.status_code == 409:
        r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_search_requires_auth(client):
    r = client.post("/search", json={"query": "EU grantovi za MSP"})
    assert r.status_code in (401, 403)


def test_search_returns_results(client):
    r = client.post(
        "/search",
        json={"query": "EU grantovi za MSP", "n_results": 3},
        headers=_auth_headers(client),
    )
    assert r.status_code == 200
    data = r.json()
    assert "results" in data
    assert "documents" in data
    assert "metadatas" in data
    assert "request_id" in data
    assert "processing_time" in data


def test_search_short_query_rejected(client):
    r = client.post("/search", json={"query": "EU"}, headers=_auth_headers(client))
    assert r.status_code == 422  # Pydantic validacija (min_length=3)


def test_search_too_many_results_rejected(client):
    r = client.post(
        "/search",
        json={"query": "grant", "n_results": 99},
        headers=_auth_headers(client),
    )
    assert r.status_code == 422  # max 20


# ---------------------------------------------------------------------------
# TESTOVI: Auth endpointi
# ---------------------------------------------------------------------------

def test_register_valid(client):
    r = client.post("/auth/register", json={
        "email": "test.user@example.com",
        "password": "sigurna123"
    })
    assert r.status_code in (200, 409)  # 409 ako već postoji
    if r.status_code == 200:
        data = r.json()
        assert "token" in data
        assert data["email"] == "test.user@example.com"
        assert data["plan"] == "free"


def test_register_invalid_email(client):
    r = client.post("/auth/register", json={
        "email": "nije-email",
        "password": "lozinka123"
    })
    assert r.status_code == 422


def test_register_short_password(client):
    r = client.post("/auth/register", json={
        "email": "validan@email.com",
        "password": "123"
    })
    assert r.status_code == 422


def test_login_wrong_credentials(client):
    r = client.post("/auth/login", json={
        "email": "nepostoji@example.com",
        "password": "pogresna"
    })
    assert r.status_code == 401


def test_auth_me_without_token(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_auth_me_invalid_token(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer laznitoken"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# TESTOVI: EUFundsAgent (izolovano s mockovima)
# ---------------------------------------------------------------------------

def test_agent_answer_returns_string():
    """EUFundsAgent.answer() mora uvijek vratiti string, čak i bez API-ja."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
         patch("ai_core.agent.genai_client.genai") as mock_genai, \
         patch("ai_core.rag_pipeline.pipeline.EmbeddingClient") as mock_emb, \
         patch("ai_core.rag_pipeline.pipeline.ChromaDBClient") as mock_db:

        mock_response = MagicMock()
        mock_response.text = "Ovo je testni odgovor o grantovima."
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        mock_emb.return_value.generate_embeddings.return_value = [[0.1] * 768]
        mock_db.return_value.client.get_or_create_collection.return_value.query.return_value = {
            "ids": [["test_id"]],
            "documents": [["Test grant dokument."]],
            "metadatas": [[{"title": "Test Grant", "category": "Test"}]],
        }

        from ai_core.agent.agent import EUFundsAgent
        agent = EUFundsAgent()
        result = agent.answer("Test upit o grantovima")

        assert isinstance(result, str), f"Očekivan string, dobiven {type(result)}"
        assert len(result) > 0, "Odgovor ne smije biti prazan string"


def test_agent_answer_handles_no_context():
    """Agent mora vratiti string čak i kad RAG ne nađe ništa."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
         patch("ai_core.agent.genai_client.genai") as mock_genai, \
         patch("ai_core.rag_pipeline.pipeline.EmbeddingClient") as mock_emb, \
         patch("ai_core.rag_pipeline.pipeline.ChromaDBClient") as mock_db:

        mock_response = MagicMock()
        mock_response.text = "Nema specifičnih podataka, ali evo opštih informacija."
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        mock_emb.return_value.generate_embeddings.return_value = [[0.1] * 768]
        mock_db.return_value.client.get_or_create_collection.return_value.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
        }

        from ai_core.agent.agent import EUFundsAgent
        agent = EUFundsAgent()
        result = agent.answer("Nešto za što nema podataka")

        assert isinstance(result, str)


def test_agent_answer_english():
    """Agent mora podržati engleski jezik."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), \
         patch("ai_core.agent.genai_client.genai") as mock_genai, \
         patch("ai_core.rag_pipeline.pipeline.EmbeddingClient") as mock_emb, \
         patch("ai_core.rag_pipeline.pipeline.ChromaDBClient") as mock_db:

        mock_response = MagicMock()
        mock_response.text = "Here are EU grants available in BiH."
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        mock_emb.return_value.generate_embeddings.return_value = [[0.1] * 768]
        mock_db.return_value.client.get_or_create_collection.return_value.query.return_value = {
            "ids": [["id1"]],
            "documents": [["EU grant document."]],
            "metadatas": [[{"title": "EU Grant", "category": "EU"}]],
        }

        from ai_core.agent.agent import EUFundsAgent
        agent = EUFundsAgent()
        result = agent.answer("What grants are available?", language="en")

        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# TESTOVI: Rate limiting
# ---------------------------------------------------------------------------

def test_rate_limit_in_memory():
    """Rate limiter mora blokirati IP koji pređe limit."""
    from backend.app.core import rate_limit

    test_ip = "192.168.99.99"
    rate_limit._rate_limit_store[test_ip] = []  # Reset

    original_limit = rate_limit.RATE_LIMIT_REQUESTS
    rate_limit.RATE_LIMIT_REQUESTS = 5  # Mali limit za test

    try:
        for i in range(5):
            result = rate_limit._check_rate_limit(test_ip)
            assert result is True, f"Zahtjev {i + 1} mora biti dozvoljen"
        blocked = rate_limit._check_rate_limit(test_ip)
        assert blocked is False, "6. zahtjev mora biti blokiran"
    finally:
        rate_limit.RATE_LIMIT_REQUESTS = original_limit
        rate_limit._rate_limit_store.pop(test_ip, None)
