"""Regression tests for the shared production ingestion contract."""

import json
from pathlib import Path

from ai_core.rag_pipeline.grant_metadata import (
    build_chroma_metadata,
    build_embedding_text,
)


GRANTS_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "grants.json"
)

LOCAL_INGEST_FILE = (
    Path(__file__).resolve().parents[2]
    / "ai_core"
    / "rag_pipeline"
    / "ingestion"
    / "ingest_local_grants.py"
)

BACKEND_INGEST_FILE = (
    Path(__file__).resolve().parents[2]
    / "backend"
    / "app"
    / "services"
    / "ai.py"
)


def _load_grants():
    return json.loads(
        GRANTS_FILE.read_text(encoding="utf-8")
    )


def test_all_records_produce_ingestion_documents():
    grants = _load_grants()

    documents = [
        build_embedding_text(grant)
        for grant in grants
    ]

    assert len(documents) == 30
    assert all(isinstance(document, str) for document in documents)
    assert all(document.strip() for document in documents)


def test_all_records_produce_chroma_metadata():
    grants = _load_grants()

    metadatas = [
        build_chroma_metadata(grant)
        for grant in grants
    ]

    assert len(metadatas) == 30
    assert all(metadata["grant_id"] for metadata in metadatas)
    assert all(metadata["title"] for metadata in metadatas)
    assert all(
        value is not None
        for metadata in metadatas
        for value in metadata.values()
    )


def test_ingestion_ids_match_serialized_grant_ids():
    grants = _load_grants()

    source_ids = [
        grant["id"]
        for grant in grants
    ]
    metadata_ids = [
        build_chroma_metadata(grant)["grant_id"]
        for grant in grants
    ]

    assert metadata_ids == source_ids
    assert len(set(metadata_ids)) == 30


def test_embedding_documents_are_deterministic():
    grants = _load_grants()

    first = [
        build_embedding_text(grant)
        for grant in grants
    ]
    second = [
        build_embedding_text(grant)
        for grant in grants
    ]

    assert first == second


def test_both_production_paths_use_shared_contract():
    local_source = LOCAL_INGEST_FILE.read_text(
        encoding="utf-8"
    )
    backend_source = BACKEND_INGEST_FILE.read_text(
        encoding="utf-8"
    )

    for source in (local_source, backend_source):
        assert "build_embedding_text" in source
        assert "build_chroma_metadata" in source

    assert "def build_embed_text" not in local_source
    assert "def metadata_text" not in local_source
    assert "def metadata_int" not in local_source


def test_list_metadata_is_available_to_search_layer():
    grant = _load_grants()[0]
    metadata = build_chroma_metadata(grant)

    assert "regions" in metadata
    assert "beneficiary_types" in metadata
    assert "sectors" in metadata
