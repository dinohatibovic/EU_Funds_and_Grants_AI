"""Fixture-driven orchestration for deterministic SEDIA incremental sync."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ai_core.rag_pipeline.grant_metadata import GrantMetadata
from ai_core.rag_pipeline.ingestion.hash_snapshot_store import (
    HashSnapshotStore,
    HashSnapshotStoreError,
)
from ai_core.rag_pipeline.ingestion.sedia_adapter import (
    sedia_response_to_grant_metadata,
)
from ai_core.rag_pipeline.ingestion.sedia_controlled_apply import (
    SediaApplyContext,
    SediaApplyMutation,
    SediaApplyReceipt,
    SediaControlledApplyError,
    SediaControlledWriter,
    SediaPreparedApply,
    SediaRollbackResult,
    build_apply_context,
    validate_apply_receipt,
    validate_prepared_apply,
    validate_rollback_result,
)
from ai_core.rag_pipeline.ingestion.sync_planner import (
    SyncAction,
    SyncPlan,
    build_hash_snapshot,
    plan_incremental_sync,
)

GrantWriter = Callable[[Sequence[GrantMetadata]], None]


class SediaIncrementalSyncError(RuntimeError):
    """Raised when orchestration cannot safely apply a SEDIA sync."""

    def __init__(
        self,
        message: str,
        *,
        run_id: str | None = None,
        transaction_id: str | None = None,
        rollback_status: str | None = None,
        recovery_required: bool = False,
    ) -> None:
        super().__init__(message)

        self.run_id = run_id
        self.transaction_id = transaction_id
        self.rollback_status = rollback_status
        self.recovery_required = recovery_required


@dataclass(frozen=True)
class SediaSyncReport:
    """Stable result contract for one incremental synchronization run."""

    source_id: str
    fetched: int
    inserted: int
    updated: int
    skipped: int
    missing_from_fetch: int
    dry_run: bool
    snapshot_saved: bool
    apply_run_id: str | None = None
    writer_transaction_id: str | None = None
    writer_receipt_validated: bool = False
    rollback_status: str | None = None
    recovery_required: bool = False

    @property
    def changed(self) -> int:
        """Return the number of records requiring a write."""

        return self.inserted + self.updated


def _changed_grants(
    plan: SyncPlan,
) -> tuple[GrantMetadata, ...]:
    """Return INSERT and UPDATE grants while preserving plan order."""

    return tuple(
        item.grant
        for item in plan.items
        if item.action
        in {
            SyncAction.INSERT,
            SyncAction.UPDATE,
        }
    )


def _target_hashes(
    previous_hashes: Mapping[str, str],
    grants: Sequence[GrantMetadata],
) -> dict[str, str]:
    """Return the no-delete target snapshot."""

    return {
        **previous_hashes,
        **build_hash_snapshot(grants),
    }


def _build_controlled_context(
    *,
    source_id: str,
    previous_hashes: Mapping[str, str],
    target_hashes: Mapping[str, str],
    plan: SyncPlan,
    changed_grants: Sequence[GrantMetadata],
) -> SediaApplyContext:
    """Build deterministic writer expectations from a sync plan."""

    return build_apply_context(
        source_id=source_id,
        previous_hashes=previous_hashes,
        target_hashes=target_hashes,
        expected_insert_count=len(
            plan.inserts
        ),
        expected_update_count=len(
            plan.updates
        ),
        changed_grant_ids=tuple(
            grant.id
            for grant in changed_grants
        ),
        mutations=tuple(
            SediaApplyMutation(
                grant_id=item.grant.id,
                action=(
                    "insert"
                    if item.action
                    is SyncAction.INSERT
                    else "update"
                ),
            )
            for item in plan.items
            if item.action
            in {
                SyncAction.INSERT,
                SyncAction.UPDATE,
            }
        ),
    )


def _attempt_controlled_rollback(
    *,
    controlled_writer: SediaControlledWriter,
    prepared: SediaPreparedApply,
    context: SediaApplyContext,
    cause: BaseException,
) -> SediaRollbackResult:
    """Attempt and validate rollback evidence."""

    try:
        rollback_result = (
            controlled_writer.rollback(
                prepared,
                cause,
            )
        )
    except Exception as rollback_error:
        raise SediaIncrementalSyncError(
            "controlled writer rollback raised "
            "an exception; manual recovery required",
            run_id=context.run_id,
            transaction_id=(
                prepared.transaction_id
            ),
            rollback_status="rollback_unknown",
            recovery_required=True,
        ) from rollback_error

    try:
        validate_rollback_result(
            rollback_result,
            context,
            prepared,
        )
    except SediaControlledApplyError as rollback_error:
        raise SediaIncrementalSyncError(
            "controlled writer returned invalid "
            "rollback evidence; manual recovery required",
            run_id=context.run_id,
            transaction_id=(
                prepared.transaction_id
            ),
            rollback_status="rollback_unknown",
            recovery_required=True,
        ) from rollback_error

    return rollback_result


def _raise_controlled_apply_failure(
    *,
    message: str,
    cause: BaseException,
    controlled_writer: SediaControlledWriter,
    prepared: SediaPreparedApply,
    context: SediaApplyContext,
) -> None:
    """Rollback one failed controlled apply and raise a stable error."""

    rollback_result = (
        _attempt_controlled_rollback(
            controlled_writer=controlled_writer,
            prepared=prepared,
            context=context,
            cause=cause,
        )
    )

    if rollback_result.rolled_back:
        raise SediaIncrementalSyncError(
            message + "; writer rollback confirmed",
            run_id=context.run_id,
            transaction_id=(
                prepared.transaction_id
            ),
            rollback_status=(
                rollback_result.status
            ),
            recovery_required=False,
        ) from cause

    raise SediaIncrementalSyncError(
        message
        + "; writer rollback was not confirmed; "
        "manual recovery required",
        run_id=context.run_id,
        transaction_id=prepared.transaction_id,
        rollback_status=rollback_result.status,
        recovery_required=True,
    ) from cause


def _apply_controlled_writer(
    *,
    controlled_writer: SediaControlledWriter,
    changed_grants: Sequence[GrantMetadata],
    context: SediaApplyContext,
    snapshot_store: HashSnapshotStore,
    source_id: str,
    target_hashes: Mapping[str, str],
) -> tuple[
    SediaPreparedApply,
    SediaApplyReceipt,
]:
    """Apply one controlled writer lifecycle and save its snapshot."""

    try:
        prepared = controlled_writer.prepare(
            changed_grants,
            context,
        )
    except Exception as prepare_error:
        raise SediaIncrementalSyncError(
            "controlled writer prepare failed",
            run_id=context.run_id,
            recovery_required=False,
        ) from prepare_error

    try:
        validate_prepared_apply(
            prepared,
            context,
        )
    except SediaControlledApplyError as prepared_error:
        _raise_controlled_apply_failure(
            message=(
                "controlled writer returned an "
                "invalid prepared handle"
            ),
            cause=prepared_error,
            controlled_writer=controlled_writer,
            prepared=prepared,
            context=context,
        )

    try:
        receipt = controlled_writer.commit(
            prepared
        )
    # A protocol implementation may raise any standard exception.
    except Exception as commit_error:  # noqa: BLE001
        _raise_controlled_apply_failure(
            message="controlled writer commit failed",
            cause=commit_error,
            controlled_writer=controlled_writer,
            prepared=prepared,
            context=context,
        )

    try:
        validate_apply_receipt(
            receipt,
            context,
            prepared,
        )
    except SediaControlledApplyError as receipt_error:
        _raise_controlled_apply_failure(
            message=(
                "controlled writer returned an "
                "invalid commit receipt"
            ),
            cause=receipt_error,
            controlled_writer=controlled_writer,
            prepared=prepared,
            context=context,
        )

    try:
        snapshot_store.save(
            source_id,
            target_hashes,
        )
    except HashSnapshotStoreError as snapshot_error:
        _raise_controlled_apply_failure(
            message=(
                "snapshot save failed after "
                "controlled writer commit"
            ),
            cause=snapshot_error,
            controlled_writer=controlled_writer,
            prepared=prepared,
            context=context,
        )

    return prepared, receipt


def run_sedia_incremental_sync(
    *,
    payload: Mapping[str, Any],
    snapshot_store: HashSnapshotStore,
    source_id: str = "eu_sedia",
    writer: GrantWriter | None = None,
    controlled_writer: (
        SediaControlledWriter | None
    ) = None,
    dry_run: bool = True,
) -> SediaSyncReport:
    """Plan and optionally apply one fixture-driven SEDIA sync.

    Dry-run is fully read-only. Legacy callable writers retain their
    existing behavior. A controlled writer uses prepare, commit,
    receipt validation and rollback evidence before the target
    snapshot is accepted.

    Hashes missing from the current fetch remain preserved because
    destructive deletion is intentionally unsupported.
    """

    if (
        writer is not None
        and controlled_writer is not None
    ):
        raise SediaIncrementalSyncError(
            "legacy writer and controlled_writer "
            "cannot be used together"
        )

    previous_hashes = snapshot_store.load(
        source_id
    )

    grants = sedia_response_to_grant_metadata(
        payload
    )

    plan = plan_incremental_sync(
        grants,
        previous_hashes,
    )

    current_ids = {
        grant.id
        for grant in grants
    }

    missing_from_fetch = len(
        set(previous_hashes) - current_ids
    )

    changed_grants = _changed_grants(
        plan
    )

    target_hashes = _target_hashes(
        previous_hashes,
        grants,
    )

    if dry_run:
        return SediaSyncReport(
            source_id=source_id,
            fetched=len(grants),
            inserted=len(plan.inserts),
            updated=len(plan.updates),
            skipped=len(plan.skips),
            missing_from_fetch=missing_from_fetch,
            dry_run=True,
            snapshot_saved=False,
        )

    if (
        changed_grants
        and writer is None
        and controlled_writer is None
    ):
        raise SediaIncrementalSyncError(
            "writer or controlled_writer is required "
            "when changes need to be applied"
        )

    if controlled_writer is not None:
        if changed_grants:
            context = _build_controlled_context(
                source_id=source_id,
                previous_hashes=previous_hashes,
                target_hashes=target_hashes,
                plan=plan,
                changed_grants=changed_grants,
            )

            prepared, _receipt = (
                _apply_controlled_writer(
                    controlled_writer=(
                        controlled_writer
                    ),
                    changed_grants=(
                        changed_grants
                    ),
                    context=context,
                    snapshot_store=(
                        snapshot_store
                    ),
                    source_id=source_id,
                    target_hashes=target_hashes,
                )
            )

            return SediaSyncReport(
                source_id=source_id,
                fetched=len(grants),
                inserted=len(plan.inserts),
                updated=len(plan.updates),
                skipped=len(plan.skips),
                missing_from_fetch=(
                    missing_from_fetch
                ),
                dry_run=False,
                snapshot_saved=True,
                apply_run_id=context.run_id,
                writer_transaction_id=(
                    prepared.transaction_id
                ),
                writer_receipt_validated=True,
            )

        snapshot_store.save(
            source_id,
            target_hashes,
        )

        return SediaSyncReport(
            source_id=source_id,
            fetched=len(grants),
            inserted=0,
            updated=0,
            skipped=len(plan.skips),
            missing_from_fetch=missing_from_fetch,
            dry_run=False,
            snapshot_saved=True,
        )

    if writer is not None and changed_grants:
        writer(changed_grants)

    snapshot_store.save(
        source_id,
        target_hashes,
    )

    return SediaSyncReport(
        source_id=source_id,
        fetched=len(grants),
        inserted=len(plan.inserts),
        updated=len(plan.updates),
        skipped=len(plan.skips),
        missing_from_fetch=missing_from_fetch,
        dry_run=False,
        snapshot_saved=True,
    )
