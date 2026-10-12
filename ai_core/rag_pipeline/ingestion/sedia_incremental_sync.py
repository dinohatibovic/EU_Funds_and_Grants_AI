"""Fixture-driven orchestration for deterministic SEDIA incremental sync."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ai_core.rag_pipeline.grant_metadata import GrantMetadata
from ai_core.rag_pipeline.ingestion.hash_snapshot_store import (
    HashSnapshotStore,
)
from ai_core.rag_pipeline.ingestion.sedia_adapter import (
    sedia_response_to_grant_metadata,
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


def run_sedia_incremental_sync(
    *,
    payload: Mapping[str, Any],
    snapshot_store: HashSnapshotStore,
    source_id: str = "eu_sedia",
    writer: GrantWriter | None = None,
    dry_run: bool = True,
) -> SediaSyncReport:
    """Plan and optionally apply one fixture-driven SEDIA sync.

    Dry-run is fully read-only. During an apply run, the snapshot is
    committed only after the writer completes successfully. Hashes for
    records missing from the current fetch are preserved because this
    prototype does not implement destructive deletion.
    """

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

    if changed_grants and writer is None:
        raise SediaIncrementalSyncError(
            "writer is required when changes need to be applied"
        )

    if writer is not None and changed_grants:
        writer(changed_grants)

    current_hashes = {
        **previous_hashes,
        **build_hash_snapshot(grants),
    }

    snapshot_store.save(
        source_id,
        current_hashes,
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
