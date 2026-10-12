"""Tests for fixture-driven SEDIA incremental sync orchestration."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from ai_core.rag_pipeline.ingestion.hash_snapshot_store import (
    HashSnapshotStore,
)
from ai_core.rag_pipeline.ingestion.sedia_incremental_sync import (
    SediaIncrementalSyncError,
    run_sedia_incremental_sync,
)
from ai_core.rag_pipeline.ingestion.sync_planner import (
    SyncPlannerError,
)

FIXTURE_PATH = Path(
    "backend/app/integrations/sedia/fixtures/"
    "search_response_minimal.json"
)


class FakeWriter:
    """Record non-destructive writer calls."""

    def __init__(
        self,
        *,
        fail: bool = False,
    ) -> None:
        self.fail = fail
        self.calls: list[tuple] = []

    def __call__(
        self,
        grants,
    ) -> None:
        self.calls.append(
            tuple(grants)
        )

        if self.fail:
            raise RuntimeError(
                "writer failed"
            )


def load_fixture() -> dict:
    """Load a fresh copy of the versioned fixture."""

    return json.loads(
        FIXTURE_PATH.read_text(
            encoding="utf-8"
        )
    )


def second_record() -> dict:
    """Return another valid synthetic SEDIA grant record."""

    return {
        "reference": "TEST-TOPIC-002",
        "summary": "Second synthetic SEDIA fixture",
        "metadata": {
            "title": [
                "Second structured grant title",
            ],
            "callTitle": [
                "Second structured call",
            ],
            "identifier": [
                "TEST-CALL-002",
            ],
            "frameworkProgramme": [
                "TEST-PROGRAMME",
            ],
            "status": [
                "OPEN",
            ],
        },
    }


def apply_fixture(
    store,
    payload=None,
):
    """Apply a payload and return its report and writer."""

    writer = FakeWriter()

    report = run_sedia_incremental_sync(
        payload=payload or load_fixture(),
        snapshot_store=store,
        writer=writer,
        dry_run=False,
    )

    return report, writer


def test_dry_run_is_fully_read_only(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    writer = FakeWriter()

    report = run_sedia_incremental_sync(
        payload=load_fixture(),
        snapshot_store=store,
        writer=writer,
        dry_run=True,
    )

    assert report.fetched == 1
    assert report.inserted == 1
    assert report.updated == 0
    assert report.skipped == 0
    assert report.changed == 1
    assert report.dry_run is True
    assert report.snapshot_saved is False
    assert writer.calls == []
    assert store.load("eu_sedia") == {}


def test_first_apply_writes_insert_and_snapshot(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)

    report, writer = apply_fixture(
        store
    )

    assert report.fetched == 1
    assert report.inserted == 1
    assert report.updated == 0
    assert report.skipped == 0
    assert report.changed == 1
    assert report.dry_run is False
    assert report.snapshot_saved is True

    assert len(writer.calls) == 1

    assert [
        grant.id
        for grant in writer.calls[0]
    ] == [
        "TEST-TOPIC-001",
    ]

    assert set(
        store.load("eu_sedia")
    ) == {
        "TEST-TOPIC-001",
    }


def test_identical_second_apply_is_skip(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)

    apply_fixture(store)

    report, writer = apply_fixture(
        store
    )

    assert report.fetched == 1
    assert report.inserted == 0
    assert report.updated == 0
    assert report.skipped == 1
    assert report.changed == 0
    assert report.snapshot_saved is True
    assert writer.calls == []


def test_changed_record_is_update(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)

    apply_fixture(store)

    changed = load_fixture()
    changed["results"][0]["metadata"]["title"] = [
        "Updated structured grant title",
    ]

    report, writer = apply_fixture(
        store,
        changed,
    )

    assert report.fetched == 1
    assert report.inserted == 0
    assert report.updated == 1
    assert report.skipped == 0
    assert report.changed == 1

    assert len(writer.calls) == 1

    assert writer.calls[0][0].id == (
        "TEST-TOPIC-001"
    )

    assert writer.calls[0][0].title == (
        "Updated structured grant title"
    )


def test_new_record_is_insert(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)

    apply_fixture(store)

    expanded = load_fixture()
    expanded["results"].append(
        second_record()
    )

    report, writer = apply_fixture(
        store,
        expanded,
    )

    assert report.fetched == 2
    assert report.inserted == 1
    assert report.updated == 0
    assert report.skipped == 1
    assert report.changed == 1

    assert len(writer.calls) == 1

    assert [
        grant.id
        for grant in writer.calls[0]
    ] == [
        "TEST-TOPIC-002",
    ]


def test_writer_failure_preserves_snapshot(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)

    apply_fixture(store)

    original_hashes = store.load(
        "eu_sedia"
    )

    changed = load_fixture()
    changed["results"][0]["metadata"]["title"] = [
        "Writer failure structured update",
    ]

    failing_writer = FakeWriter(
        fail=True
    )

    with pytest.raises(
        RuntimeError,
        match="writer failed",
    ):
        run_sedia_incremental_sync(
            payload=changed,
            snapshot_store=store,
            writer=failing_writer,
            dry_run=False,
        )

    assert len(failing_writer.calls) == 1

    assert store.load(
        "eu_sedia"
    ) == original_hashes


def test_apply_requires_writer_for_changes(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)

    with pytest.raises(
        SediaIncrementalSyncError,
        match="writer is required",
    ):
        run_sedia_incremental_sync(
            payload=load_fixture(),
            snapshot_store=store,
            writer=None,
            dry_run=False,
        )

    assert store.load("eu_sedia") == {}


def test_invalid_fixture_is_rejected_before_write(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    writer = FakeWriter()

    invalid_payload = {
        "results": [
            {
                "reference": "missing-title",
                "metadata": {
                    "identifier": [
                        "TEST-CALL-INVALID",
                    ],
                    "frameworkProgramme": [
                        "TEST-PROGRAMME",
                    ],
                    "status": [
                        "OPEN",
                    ],
                },
            },
        ],
    }

    with pytest.raises(
        ValueError,
        match="structured grant title",
    ):
        run_sedia_incremental_sync(
            payload=invalid_payload,
            snapshot_store=store,
            writer=writer,
            dry_run=False,
        )

    assert writer.calls == []
    assert store.load("eu_sedia") == {}


def test_duplicate_ids_fail_before_write(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    writer = FakeWriter()
    payload = load_fixture()

    payload["results"].append(
        deepcopy(payload["results"][0])
    )

    with pytest.raises(
        SyncPlannerError,
        match="duplicate grant id",
    ):
        run_sedia_incremental_sync(
            payload=payload,
            snapshot_store=store,
            writer=writer,
            dry_run=False,
        )

    assert writer.calls == []
    assert store.load("eu_sedia") == {}


def test_missing_record_is_preserved_without_delete(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    expanded = load_fixture()

    expanded["results"].append(
        second_record()
    )

    first_report, first_writer = apply_fixture(
        store,
        expanded,
    )

    assert first_report.inserted == 2
    assert first_report.missing_from_fetch == 0
    assert len(first_writer.calls) == 1

    report, writer = apply_fixture(
        store,
        load_fixture(),
    )

    assert report.fetched == 1
    assert report.missing_from_fetch == 1
    assert report.inserted == 0
    assert report.updated == 0
    assert report.skipped == 1
    assert report.changed == 0
    assert writer.calls == []

    assert set(
        store.load("eu_sedia")
    ) == {
        "TEST-TOPIC-001",
        "TEST-TOPIC-002",
    }
