"""Fixture-only integration of Chroma writer and SEDIA orchestration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_core.rag_pipeline.ingestion.hash_snapshot_store import (
    HashSnapshotStore,
    HashSnapshotStoreError,
)
from ai_core.rag_pipeline.ingestion.sedia_chroma_partial_upsert import (
    SediaChromaFixtureCollection,
    SediaChromaFixtureControlledWriter,
)
from ai_core.rag_pipeline.ingestion.sedia_incremental_sync import (
    SediaIncrementalSyncError,
    run_sedia_incremental_sync,
)

FIXTURE_PATH = Path(
    "backend/app/integrations/sedia/fixtures/"
    "search_response_minimal.json"
)


def load_payload() -> dict:
    return json.loads(
        FIXTURE_PATH.read_text(
            encoding="utf-8"
        )
    )


def embedding_provider(
    documents: tuple[str, ...],
):
    return tuple(
        (
            float(index + 1),
            float(index + 2),
            float(index + 3),
        )
        for index, _document in enumerate(
            documents
        )
    )


def build_writer(
    collection: SediaChromaFixtureCollection,
) -> SediaChromaFixtureControlledWriter:
    return SediaChromaFixtureControlledWriter(
        collection=collection,
        embedding_provider=embedding_provider,
    )


class FailingSaveStore(HashSnapshotStore):
    """Fixture store whose snapshot save always fails."""

    def save(
        self,
        source_id,
        hashes,
    ):
        raise HashSnapshotStoreError(
            "fixture snapshot save failed"
        )


def test_orchestrator_commits_fixture_writer_and_snapshot(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    collection = SediaChromaFixtureCollection()
    writer = build_writer(collection)

    report = run_sedia_incremental_sync(
        payload=load_payload(),
        snapshot_store=store,
        controlled_writer=writer,
        dry_run=False,
    )

    assert report.inserted == 1
    assert report.updated == 0
    assert report.changed == 1
    assert report.snapshot_saved is True
    assert report.writer_receipt_validated is True
    assert report.apply_run_id is not None
    assert report.writer_transaction_id is not None
    assert report.rollback_status is None
    assert report.recovery_required is False

    records = collection.snapshot()

    assert tuple(
        record.grant_id
        for record in records
    ) == (
        "TEST-TOPIC-001",
    )

    assert set(store.load("eu_sedia")) == {
        "TEST-TOPIC-001",
    }

    assert len(collection.upsert_calls) == 1
    assert collection.delete_calls == []


def test_orchestrator_dry_run_does_not_call_fixture_writer(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    collection = SediaChromaFixtureCollection()
    writer = build_writer(collection)

    report = run_sedia_incremental_sync(
        payload=load_payload(),
        snapshot_store=store,
        controlled_writer=writer,
        dry_run=True,
    )

    assert report.dry_run is True
    assert report.changed == 1
    assert report.snapshot_saved is False
    assert report.apply_run_id is None

    assert collection.snapshot() == ()
    assert collection.get_calls == []
    assert collection.upsert_calls == []
    assert collection.delete_calls == []
    assert store.load("eu_sedia") == {}


def test_orchestrator_partial_commit_failure_rolls_back(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    collection = SediaChromaFixtureCollection(
        fail_upsert_after=0,
    )
    writer = build_writer(collection)

    with pytest.raises(
        SediaIncrementalSyncError,
        match="commit failed",
    ) as exc_info:
        run_sedia_incremental_sync(
            payload=load_payload(),
            snapshot_store=store,
            controlled_writer=writer,
            dry_run=False,
        )

    assert (
        exc_info.value.rollback_status
        == "rolled_back"
    )
    assert (
        exc_info.value.recovery_required
        is False
    )

    assert collection.snapshot() == ()
    assert store.load("eu_sedia") == {}
    assert len(collection.upsert_calls) == 1
    assert collection.delete_calls == [
        (
            "TEST-TOPIC-001",
        )
    ]


def test_snapshot_failure_after_commit_restores_collection(
    tmp_path,
):
    store = FailingSaveStore(tmp_path)
    collection = SediaChromaFixtureCollection()
    writer = build_writer(collection)

    with pytest.raises(
        SediaIncrementalSyncError,
        match="snapshot save failed",
    ) as exc_info:
        run_sedia_incremental_sync(
            payload=load_payload(),
            snapshot_store=store,
            controlled_writer=writer,
            dry_run=False,
        )

    assert (
        exc_info.value.rollback_status
        == "rolled_back"
    )
    assert (
        exc_info.value.recovery_required
        is False
    )

    assert collection.snapshot() == ()
    assert len(collection.upsert_calls) == 1
    assert collection.delete_calls == [
        (
            "TEST-TOPIC-001",
        )
    ]


def test_second_identical_run_skips_writer_lifecycle(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    collection = SediaChromaFixtureCollection()
    first_writer = build_writer(collection)

    first = run_sedia_incremental_sync(
        payload=load_payload(),
        snapshot_store=store,
        controlled_writer=first_writer,
        dry_run=False,
    )

    assert first.changed == 1
    assert first.snapshot_saved is True

    calls_after_first = (
        len(collection.get_calls),
        len(collection.upsert_calls),
        len(collection.delete_calls),
    )

    second_writer = build_writer(collection)

    second = run_sedia_incremental_sync(
        payload=load_payload(),
        snapshot_store=store,
        controlled_writer=second_writer,
        dry_run=False,
    )

    assert second.changed == 0
    assert second.skipped == 1
    assert second.snapshot_saved is True
    assert second.apply_run_id is None
    assert (
        second.writer_receipt_validated
        is False
    )

    assert (
        len(collection.get_calls),
        len(collection.upsert_calls),
        len(collection.delete_calls),
    ) == calls_after_first
