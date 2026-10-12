"""Read-only bridge from SEDIA fetching to incremental planning."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ai_core.rag_pipeline.ingestion.hash_snapshot_store import (
    HashSnapshotStore,
)
from ai_core.rag_pipeline.ingestion.sedia_incremental_sync import (
    SediaSyncReport,
    run_sedia_incremental_sync,
)

from .fetcher import (
    RetryablePredicate,
    SediaFetchResult,
    SediaSearchClient,
    SleepCallable,
    fetch_sedia_pages,
    is_retryable_sedia_error,
)


@dataclass(frozen=True)
class SediaDryRunResult:
    """Combined result of fetching and incremental dry-run planning."""

    fetch: SediaFetchResult
    sync: SediaSyncReport

    @property
    def pages_fetched(self) -> int:
        """Return the number of successfully fetched pages."""

        return self.fetch.pages_fetched

    @property
    def records_fetched(self) -> int:
        """Return the number of fetched raw records."""

        return self.fetch.records_fetched


async def run_sedia_fetch_dry_run(
    *,
    client: SediaSearchClient,
    snapshot_store: HashSnapshotStore,
    source_id: str = "eu_sedia",
    text: str = "",
    filters: Mapping[str, Any] | None = None,
    page_size: int = 100,
    max_pages: int = 100,
    max_attempts: int = 1,
    retry_delays: Sequence[float] = (1.0, 2.0),
    retryable: RetryablePredicate = (
        is_retryable_sedia_error
    ),
    sleep: SleepCallable,
) -> SediaDryRunResult:
    """Fetch SEDIA pages and perform a fully read-only sync dry-run.

    This bridge deliberately exposes no writer and no apply mode.
    The incremental orchestrator is always called with ``dry_run=True``.
    """

    fetch = await fetch_sedia_pages(
        client=client,
        text=text,
        filters=filters,
        page_size=page_size,
        max_pages=max_pages,
        max_attempts=max_attempts,
        retry_delays=retry_delays,
        retryable=retryable,
        sleep=sleep,
    )

    sync = run_sedia_incremental_sync(
        payload=fetch.payload,
        snapshot_store=snapshot_store,
        source_id=source_id,
        writer=None,
        dry_run=True,
    )

    if fetch.records_fetched != sync.fetched:
        raise RuntimeError(
            "SEDIA fetch and normalized record counts differ"
        )

    return SediaDryRunResult(
        fetch=fetch,
        sync=sync,
    )
