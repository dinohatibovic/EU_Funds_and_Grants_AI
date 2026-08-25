from pathlib import Path

from ai_core.vector_store.chroma_client import (
    DEFAULT_CHROMA_COLLECTION,
)


PRODUCTION_FILES = (
    Path("ai_core/vector_store/chroma_client.py"),
    Path("ai_core/rag_pipeline/ingestion/ingest_local_grants.py"),
    Path("ai_core/rag_pipeline/ingestion/ingest_sample.py"),
    Path("ai_core/rag_pipeline/pipeline.py"),
)


def test_default_chroma_collection_contract():
    assert DEFAULT_CHROMA_COLLECTION == "eu_grants"

    literal_files = []

    for path in PRODUCTION_FILES:
        source = path.read_text(encoding="utf-8")

        if '"eu_grants"' in source:
            literal_files.append(path)

    assert literal_files == [Path("ai_core/vector_store/chroma_client.py")]


def test_collection_consumers_use_shared_constant():
    for path in PRODUCTION_FILES[1:]:
        source = path.read_text(encoding="utf-8")

        assert "DEFAULT_CHROMA_COLLECTION" in source
        assert '"eu_grants"' not in source
