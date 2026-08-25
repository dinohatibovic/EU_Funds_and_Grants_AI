from unittest.mock import MagicMock

import pytest

from ai_core.vector_store.chroma_client import (
    ChromaDBClient,
)


def _client_with_collection():
    client = object.__new__(ChromaDBClient)
    client.collection = MagicMock()
    return client


def _batch():
    return {
        "documents": ["grant one", "grant two"],
        "metadatas": [
            {"status": "verified"},
            {"status": "rolling"},
        ],
        "ids": ["grant-1", "grant-2"],
        "embeddings": [
            [0.1, 0.2],
            [0.3, 0.4],
        ],
    }


def test_sync_documents_upserts_complete_batch():
    client = _client_with_collection()
    batch = _batch()

    client.collection.get.return_value = {
        "ids": ["grant-1", "grant-2"],
    }
    client.collection.count.return_value = 2

    result = client.sync_documents(**batch)

    client.collection.upsert.assert_called_once_with(
        ids=batch["ids"],
        embeddings=batch["embeddings"],
        metadatas=batch["metadatas"],
        documents=batch["documents"],
    )
    client.collection.delete.assert_not_called()
    assert result == 2


def test_sync_documents_deletes_only_stale_ids():
    client = _client_with_collection()
    batch = _batch()

    client.collection.get.return_value = {
        "ids": [
            "grant-1",
            "grant-2",
            "grant-old",
        ],
    }
    client.collection.count.return_value = 2

    result = client.sync_documents(**batch)

    client.collection.upsert.assert_called_once()
    client.collection.delete.assert_called_once_with(
        ids=["grant-old"]
    )
    assert result == 2


def test_upsert_failure_does_not_delete_existing_records():
    client = _client_with_collection()
    batch = _batch()

    client.collection.get.return_value = {
        "ids": ["grant-old"],
    }
    client.collection.upsert.side_effect = RuntimeError(
        "upsert failed"
    )

    with pytest.raises(RuntimeError, match="upsert failed"):
        client.sync_documents(**batch)

    client.collection.delete.assert_not_called()
    client.collection.count.assert_not_called()


@pytest.mark.parametrize(
    "changes, message",
    [
        (
            {"documents": []},
            "equal lengths",
        ),
        (
            {"ids": []},
            "At least one document",
        ),
        (
            {"ids": ["grant-1", "grant-1"]},
            "unique",
        ),
    ],
)
def test_sync_documents_validates_before_writing(
    changes,
    message,
):
    client = _client_with_collection()
    batch = _batch()
    batch.update(changes)

    with pytest.raises(ValueError, match=message):
        client.sync_documents(**batch)

    client.collection.get.assert_not_called()
    client.collection.upsert.assert_not_called()
    client.collection.delete.assert_not_called()
