from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ai_core.embeddings.embedding_client import (
    DEFAULT_EMBEDDING_MODEL,
    EmbeddingClient,
)


def test_embedding_client_uses_default_model(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    embedding = SimpleNamespace(values=[0.1, 0.2, 0.3])
    response = SimpleNamespace(embeddings=[embedding])
    client = MagicMock()
    client.models.embed_content.return_value = response

    with patch(
        "ai_core.embeddings.embedding_client.genai.Client",
        return_value=client,
    ):
        embedding_client = EmbeddingClient()
        result = embedding_client.generate_embeddings(
            ["Test grant"]
        )

    assert embedding_client.model_name == DEFAULT_EMBEDDING_MODEL
    assert result == [[0.1, 0.2, 0.3]]

    client.models.embed_content.assert_called_once_with(
        model=DEFAULT_EMBEDDING_MODEL,
        contents=["Test grant"],
    )
