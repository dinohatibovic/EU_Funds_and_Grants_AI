"""Integration tests for controlled SEDIA apply orchestration."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from ai_core.rag_pipeline.ingestion.hash_snapshot_store import (
    HashSnapshotStore,
    HashSnapshotStoreError,
)
from ai_core.rag_pipeline.ingestion.sedia_controlled_apply import (
    SediaApplyContext,
    SediaApplyReceipt,
    SediaPreparedApply,
    SediaRollbackResult,
)
from ai_core.rag_pipeline.ingestion.sedia_incremental_sync import (
    SediaIncrementalSyncError,
    run_sedia_incremental_sync,
)

FIXTURE_PATH = Path(
    "backend/app/integrations/sedia/fixtures/"
    "search_response_minimal.json"
)


def load_fixture() -> dict:
    """Return a fresh synthetic SEDIA response."""

    return json.loads(
        FIXTURE_PATH.read_text(
            encoding="utf-8"
        )
    )


class ControlledFakeWriter:
    """Record a configurable fixture-only writer lifecycle."""

    def __init__(
        self,
        *,
        prepare_error: BaseException | None = None,
        commit_error: BaseException | None = None,
        rollback_error: BaseException | None = None,
        rollback_status: str = "rolled_back",
        invalid_prepared: bool = False,
        invalid_receipt: bool = False,
    ) -> None:
        self.prepare_error = prepare_error
        self.commit_error = commit_error
        self.rollback_error = rollback_error
        self.rollback_status = rollback_status
        self.invalid_prepared = invalid_prepared
        self.invalid_receipt = invalid_receipt

        self.prepare_calls: list[tuple] = []
        self.commit_calls: list[
            SediaPreparedApply
        ] = []
        self.rollback_calls: list[tuple] = []

        self.context: SediaApplyContext | None = None

    def prepare(
        self,
        grants,
        context: SediaApplyContext,
    ) -> SediaPreparedApply:
        self.prepare_calls.append(
            tuple(grants)
        )
        self.context = context

        if self.prepare_error is not None:
            raise self.prepare_error

        prepared = SediaPreparedApply(
            run_id=context.run_id,
            transaction_id="txn-fixture-001",
            prepared_grant_ids=(
                context.changed_grant_ids
            ),
        )

        if self.invalid_prepared:
            return replace(
                prepared,
                run_id="invalid-run",
            )

        return prepared

    def commit(
        self,
        prepared: SediaPreparedApply,
    ) -> SediaApplyReceipt:
        self.commit_calls.append(
            prepared
        )

        if self.commit_error is not None:
            raise self.commit_error

        assert self.context is not None

        receipt = SediaApplyReceipt(
            run_id=self.context.run_id,
            transaction_id=(
                prepared.transaction_id
            ),
            committed_insert_count=(
                self.context.expected_insert_count
            ),
            committed_update_count=(
                self.context.expected_update_count
            ),
            committed_grant_ids=(
                self.context.changed_grant_ids
            ),
            committed=True,
        )

        if self.invalid_receipt:
            return replace(
                receipt,
                committed_insert_count=(
                    receipt.committed_insert_count
                    + 1
                ),
            )

        return receipt

    def rollback(
        self,
        prepared: SediaPreparedApply,
        cause: BaseException,
    ) -> SediaRollbackResult:
        self.rollback_calls.append(
            (
                prepared,
                cause,
            )
        )

        if self.rollback_error is not None:
            raise self.rollback_error

        assert self.context is not None

        return SediaRollbackResult(
            run_id=self.context.run_id,
            transaction_id=(
                prepared.transaction_id
            ),
            status=self.rollback_status,
            detail=(
                ""
                if self.rollback_status
                == "rolled_back"
                else "fixture rollback not confirmed"
            ),
        )


class FailingSaveStore(HashSnapshotStore):
    """Fixture store whose save always fails."""

    def save(
        self,
        source_id,
        hashes,
    ):
        raise HashSnapshotStoreError(
            "fixture snapshot save failed"
        )


def test_controlled_apply_commits_and_saves_snapshot(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    writer = ControlledFakeWriter()

    report = run_sedia_incremental_sync(
        payload=load_fixture(),
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
    assert report.writer_transaction_id == (
        "txn-fixture-001"
    )
    assert report.rollback_status is None
    assert report.recovery_required is False

    assert len(writer.prepare_calls) == 1
    assert len(writer.commit_calls) == 1
    assert writer.rollback_calls == []

    assert set(store.load("eu_sedia")) == {
        "TEST-TOPIC-001",
    }


def test_controlled_apply_context_is_deterministic(
    tmp_path,
):
    first_store = HashSnapshotStore(
        tmp_path / "first"
    )
    second_store = HashSnapshotStore(
        tmp_path / "second"
    )
    first_writer = ControlledFakeWriter()
    second_writer = ControlledFakeWriter()

    first = run_sedia_incremental_sync(
        payload=load_fixture(),
        snapshot_store=first_store,
        controlled_writer=first_writer,
        dry_run=False,
    )
    second = run_sedia_incremental_sync(
        payload=load_fixture(),
        snapshot_store=second_store,
        controlled_writer=second_writer,
        dry_run=False,
    )

    assert first.apply_run_id == second.apply_run_id
    assert first_writer.context == second_writer.context


def test_controlled_writer_not_called_in_dry_run(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    writer = ControlledFakeWriter()

    report = run_sedia_incremental_sync(
        payload=load_fixture(),
        snapshot_store=store,
        controlled_writer=writer,
        dry_run=True,
    )

    assert report.dry_run is True
    assert report.snapshot_saved is False
    assert report.apply_run_id is None
    assert writer.prepare_calls == []
    assert writer.commit_calls == []
    assert writer.rollback_calls == []
    assert store.load("eu_sedia") == {}


def test_no_change_apply_skips_writer_lifecycle(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    first_writer = ControlledFakeWriter()

    run_sedia_incremental_sync(
        payload=load_fixture(),
        snapshot_store=store,
        controlled_writer=first_writer,
        dry_run=False,
    )

    second_writer = ControlledFakeWriter()

    report = run_sedia_incremental_sync(
        payload=load_fixture(),
        snapshot_store=store,
        controlled_writer=second_writer,
        dry_run=False,
    )

    assert report.changed == 0
    assert report.skipped == 1
    assert report.snapshot_saved is True
    assert report.apply_run_id is None
    assert (
        report.writer_receipt_validated
        is False
    )
    assert second_writer.prepare_calls == []
    assert second_writer.commit_calls == []
    assert second_writer.rollback_calls == []


def test_prepare_failure_does_not_attempt_rollback(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    writer = ControlledFakeWriter(
        prepare_error=RuntimeError(
            "fixture prepare failed"
        )
    )

    with pytest.raises(
        SediaIncrementalSyncError,
        match="prepare failed",
    ) as exc_info:
        run_sedia_incremental_sync(
            payload=load_fixture(),
            snapshot_store=store,
            controlled_writer=writer,
            dry_run=False,
        )

    assert exc_info.value.run_id is not None
    assert (
        exc_info.value.recovery_required
        is False
    )
    assert writer.commit_calls == []
    assert writer.rollback_calls == []
    assert store.load("eu_sedia") == {}


def test_invalid_prepared_handle_rolls_back(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    writer = ControlledFakeWriter(
        invalid_prepared=True
    )

    with pytest.raises(
        SediaIncrementalSyncError,
        match="invalid prepared handle",
    ) as exc_info:
        run_sedia_incremental_sync(
            payload=load_fixture(),
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
    assert writer.commit_calls == []
    assert len(writer.rollback_calls) == 1
    assert store.load("eu_sedia") == {}


def test_commit_failure_rolls_back_and_preserves_snapshot(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    writer = ControlledFakeWriter(
        commit_error=RuntimeError(
            "fixture commit failed"
        )
    )

    with pytest.raises(
        SediaIncrementalSyncError,
        match="commit failed",
    ) as exc_info:
        run_sedia_incremental_sync(
            payload=load_fixture(),
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
    assert len(writer.prepare_calls) == 1
    assert len(writer.commit_calls) == 1
    assert len(writer.rollback_calls) == 1
    assert store.load("eu_sedia") == {}


def test_invalid_receipt_rolls_back_and_preserves_snapshot(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    writer = ControlledFakeWriter(
        invalid_receipt=True
    )

    with pytest.raises(
        SediaIncrementalSyncError,
        match="invalid commit receipt",
    ) as exc_info:
        run_sedia_incremental_sync(
            payload=load_fixture(),
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
    assert len(writer.rollback_calls) == 1
    assert store.load("eu_sedia") == {}


def test_snapshot_failure_after_commit_rolls_back(
    tmp_path,
):
    store = FailingSaveStore(tmp_path)
    writer = ControlledFakeWriter()

    with pytest.raises(
        SediaIncrementalSyncError,
        match="snapshot save failed",
    ) as exc_info:
        run_sedia_incremental_sync(
            payload=load_fixture(),
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
    assert len(writer.commit_calls) == 1
    assert len(writer.rollback_calls) == 1
    assert store.load("eu_sedia") == {}


@pytest.mark.parametrize(
    "rollback_status",
    [
        "rollback_failed",
        "rollback_unknown",
    ],
)
def test_unconfirmed_rollback_requires_recovery(
    tmp_path,
    rollback_status,
):
    store = HashSnapshotStore(tmp_path)
    writer = ControlledFakeWriter(
        commit_error=RuntimeError(
            "fixture commit failed"
        ),
        rollback_status=rollback_status,
    )

    with pytest.raises(
        SediaIncrementalSyncError,
        match="manual recovery required",
    ) as exc_info:
        run_sedia_incremental_sync(
            payload=load_fixture(),
            snapshot_store=store,
            controlled_writer=writer,
            dry_run=False,
        )

    assert (
        exc_info.value.rollback_status
        == rollback_status
    )
    assert (
        exc_info.value.recovery_required
        is True
    )
    assert store.load("eu_sedia") == {}


def test_rollback_exception_requires_recovery(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    writer = ControlledFakeWriter(
        commit_error=RuntimeError(
            "fixture commit failed"
        ),
        rollback_error=RuntimeError(
            "fixture rollback crashed"
        ),
    )

    with pytest.raises(
        SediaIncrementalSyncError,
        match="rollback raised",
    ) as exc_info:
        run_sedia_incremental_sync(
            payload=load_fixture(),
            snapshot_store=store,
            controlled_writer=writer,
            dry_run=False,
        )

    assert (
        exc_info.value.rollback_status
        == "rollback_unknown"
    )
    assert (
        exc_info.value.recovery_required
        is True
    )
    assert store.load("eu_sedia") == {}


def test_legacy_and_controlled_writer_are_exclusive(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    controlled_writer = ControlledFakeWriter()

    with pytest.raises(
        SediaIncrementalSyncError,
        match="cannot be used together",
    ):
        run_sedia_incremental_sync(
            payload=load_fixture(),
            snapshot_store=store,
            writer=lambda grants: None,
            controlled_writer=controlled_writer,
            dry_run=False,
        )

    assert controlled_writer.prepare_calls == []
    assert store.load("eu_sedia") == {}


def test_legacy_callable_writer_remains_supported(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)
    calls = []

    report = run_sedia_incremental_sync(
        payload=load_fixture(),
        snapshot_store=store,
        writer=lambda grants: calls.append(
            tuple(grants)
        ),
        dry_run=False,
    )

    assert report.changed == 1
    assert report.snapshot_saved is True
    assert report.apply_run_id is None
    assert (
        report.writer_receipt_validated
        is False
    )
    assert len(calls) == 1
    assert set(store.load("eu_sedia")) == {
        "TEST-TOPIC-001",
    }
