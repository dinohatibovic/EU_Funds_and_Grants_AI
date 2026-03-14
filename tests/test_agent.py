"""
tests/test_agent.py
===================
BUG #10: Stari test direktno inicijalizovao EUFundsAgent koji poziva
pravi Gemini API — bez ključa test bi pao sa EnvironmentError.
Popravljeno: koristimo mock da izolovamo test od mrežnih poziva.
"""

from unittest.mock import MagicMock, patch


def test_answer_returns_string():
    """EUFundsAgent.answer() mora uvijek vratiti string, čak i bez API-ja."""
    with patch("agent.genai_client.genai") as mock_genai, \
         patch("rag.pipeline.EmbeddingClient") as mock_emb, \
         patch("rag.pipeline.ChromaDBClient") as mock_db:

        # Postavi mock odgovore
        mock_response = MagicMock()
        mock_response.text = "Ovo je testni odgovor o grantovima."
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        mock_emb.return_value.generate_embeddings.return_value = [[0.1] * 768]
        mock_db.return_value.client.get_or_create_collection.return_value.query.return_value = {
            "ids": [["test_id"]],
            "documents": [["Test grant dokument."]],
            "metadatas": [[{"title": "Test Grant", "category": "Test"}]],
        }

        from agent.agent import EUFundsAgent
        agent = EUFundsAgent()
        result = agent.answer("Test upit o grantovima")

        assert isinstance(result, str), f"Očekivan string, dobiven {type(result)}"
        assert len(result) > 0, "Odgovor ne smije biti prazan string"


def test_answer_handles_no_context():
    """Agent mora vratiti string čak i kad RAG ne nađe ništa."""
    with patch("agent.genai_client.genai") as mock_genai, \
         patch("rag.pipeline.EmbeddingClient") as mock_emb, \
         patch("rag.pipeline.ChromaDBClient") as mock_db:

        mock_response = MagicMock()
        mock_response.text = "Nema specifičnih podataka, ali evo opštih informacija."
        mock_genai.Client.return_value.models.generate_content.return_value = mock_response

        mock_emb.return_value.generate_embeddings.return_value = [[0.1] * 768]
        mock_db.return_value.client.get_or_create_collection.return_value.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
        }

        from agent.agent import EUFundsAgent
        agent = EUFundsAgent()
        result = agent.answer("Nešto za što nema podataka")

        assert isinstance(result, str)
