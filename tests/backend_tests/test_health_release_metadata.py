from unittest.mock import MagicMock

from ai_core.vector_store.chroma_client import (
    DEFAULT_CHROMA_COLLECTION,
)
from backend.app.api import system
from backend.app.core import config
from backend.app.services import ai as ai_services


def test_release_metadata_defaults_are_defined():
    assert config.APP_VERSION == "2.2.1"
    assert isinstance(config.GIT_COMMIT, str)
    assert config.GIT_COMMIT


def test_health_exposes_release_and_chroma_metadata(
    monkeypatch,
):
    chroma_client = MagicMock()
    chroma_client.collection.count.return_value = 30

    monkeypatch.setattr(
        ai_services,
        "chroma_client",
        chroma_client,
    )
    monkeypatch.setattr(
        ai_services,
        "embedding_client",
        MagicMock(),
    )
    monkeypatch.setattr(
        ai_services,
        "_grants_cache",
        [
            {
                "id": f"grant-{index}",
                "deadline": None,
            }
            for index in range(30)
        ],
    )
    monkeypatch.setattr(
        config,
        "APP_VERSION",
        "2.2.1",
    )
    monkeypatch.setattr(
        config,
        "GIT_COMMIT",
        "abc1234",
    )

    response = system.health_check()

    assert response["status"] == "healthy"
    assert response["version"] == "2.2.1"
    assert response["git_commit"] == "abc1234"
    assert (
        response["chroma_collection"]
        == DEFAULT_CHROMA_COLLECTION
    )
    assert response["chroma_documents"] == 30

    assert response["grants_total"] == 30
    assert response["grants_in_vector_db"] == 30
    assert response["ai_engine"] == "ready"


def test_root_uses_shared_release_version(
    monkeypatch,
):
    monkeypatch.setattr(
        config,
        "APP_VERSION",
        "2.2.1",
    )

    response = system.root()

    assert response["version"] == "2.2.1"
    assert response["status"] == "running"
