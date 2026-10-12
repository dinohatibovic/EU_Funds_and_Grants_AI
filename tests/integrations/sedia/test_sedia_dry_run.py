import asyncio
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from ai_core.rag_pipeline.ingestion.sedia_adapter import (
    SediaAdapterError,
    sedia_response_to_grant_metadata,
)
from ai_core.rag_pipeline.ingestion.sync_planner import (
    build_hash_snapshot,
)
from backend.app.integrations.sedia.dry_run import (
    run_sedia_fetch_dry_run,
)
from backend.app.integrations.sedia.exceptions import (
    SediaHTTPError,
)
from backend.app.integrations.sedia.models import (
    SediaSearchRequest,
    SediaSearchResponse,
)


def grant_record(
    reference: str,
    *,
    summary: str | None = None,
) -> dict[str, Any]:
    title = summary or f"Grant {reference}"

    return {
        "reference": reference,
        "summary": title,
        "metadata": {
            "title": [
                title,
            ],
            "callTitle": [
                f"Call {reference}",
            ],
            "identifier": [
                f"CALL-{reference}",
            ],
            "frameworkProgramme": [
                "TEST-PROGRAMME",
            ],
            "status": [
                "OPEN",
            ],
        },
    }


class FakeSediaClient:
    def __init__(
        self,
        outcomes: Sequence[object],
    ) -> None:
        self.outcomes = list(outcomes)
        self.requests: list[SediaSearchRequest] = []

    async def search(
        self,
        request: SediaSearchRequest,
    ) -> SediaSearchResponse:
        self.requests.append(request)

        index = len(self.requests) - 1

        if index >= len(self.outcomes):
            raise AssertionError(
                "unexpected extra SEDIA request"
            )

        outcome = self.outcomes[index]

        if isinstance(outcome, Exception):
            raise outcome

        if not isinstance(outcome, dict):
            raise TypeError(
                "outcome must be a response object or exception"
            )

        return SediaSearchResponse.from_payload(
            outcome
        )


class ReadOnlySnapshotStore:
    def __init__(
        self,
        hashes: Mapping[str, str] | None = None,
    ) -> None:
        self.hashes = dict(hashes or {})
        self.load_calls: list[str] = []
        self.save_calls: list[
            tuple[str, dict[str, str]]
        ] = []

    def load(
        self,
        source_id: str,
    ) -> dict[str, str]:
        self.load_calls.append(source_id)

        return dict(self.hashes)

    def save(
        self,
        source_id: str,
        hashes: Mapping[str, str],
    ) -> None:
        self.save_calls.append(
            (
                source_id,
                dict(hashes),
            )
        )

        raise AssertionError(
            "dry-run must never save a snapshot"
        )


async def no_sleep(
    delay: float,
) -> None:
    if delay < 0:
        raise AssertionError(
            "delay cannot be negative"
        )


def test_single_page_produces_insert_dry_run() -> None:
    async def scenario() -> None:
        client = FakeSediaClient(
            [
                {
                    "results": [
                        grant_record("A"),
                    ],
                },
            ]
        )
        store = ReadOnlySnapshotStore()

        result = await run_sedia_fetch_dry_run(
            client=client,
            snapshot_store=store,  # type: ignore[arg-type]
            page_size=2,
            sleep=no_sleep,
        )

        assert result.pages_fetched == 1
        assert result.records_fetched == 1
        assert result.sync.fetched == 1
        assert result.sync.inserted == 1
        assert result.sync.updated == 0
        assert result.sync.skipped == 0
        assert result.sync.dry_run is True
        assert result.sync.snapshot_saved is False
        assert store.load_calls == [
            "eu_sedia",
        ]
        assert store.save_calls == []

    asyncio.run(scenario())


def test_multiple_pages_produce_one_combined_report() -> None:
    async def scenario() -> None:
        client = FakeSediaClient(
            [
                {
                    "results": [
                        grant_record("A"),
                        grant_record("B"),
                    ],
                },
                {
                    "results": [
                        grant_record("C"),
                    ],
                },
            ]
        )
        store = ReadOnlySnapshotStore()

        result = await run_sedia_fetch_dry_run(
            client=client,
            snapshot_store=store,  # type: ignore[arg-type]
            text="digital",
            filters={
                "status": "OPEN",
            },
            page_size=2,
            sleep=no_sleep,
        )

        assert result.pages_fetched == 2
        assert result.records_fetched == 3
        assert result.sync.fetched == 3
        assert result.sync.inserted == 3
        assert result.sync.changed == 3
        assert [
            request.page_number
            for request in client.requests
        ] == [
            1,
            2,
        ]
        assert all(
            request.text == "digital"
            for request in client.requests
        )
        assert all(
            request.filters
            == {
                "status": "OPEN",
            }
            for request in client.requests
        )
        assert store.save_calls == []

    asyncio.run(scenario())


def test_existing_hash_is_planned_as_skip() -> None:
    async def scenario() -> None:
        payload = {
            "results": [
                grant_record("A"),
            ],
        }
        grants = sedia_response_to_grant_metadata(
            payload
        )
        previous_hashes = build_hash_snapshot(
            grants
        )

        client = FakeSediaClient(
            [
                payload,
            ]
        )
        store = ReadOnlySnapshotStore(
            previous_hashes
        )
        before = dict(store.hashes)

        result = await run_sedia_fetch_dry_run(
            client=client,
            snapshot_store=store,  # type: ignore[arg-type]
            page_size=2,
            sleep=no_sleep,
        )

        assert result.sync.inserted == 0
        assert result.sync.updated == 0
        assert result.sync.skipped == 1
        assert result.sync.changed == 0
        assert store.hashes == before
        assert store.save_calls == []

    asyncio.run(scenario())


def test_retry_settings_are_forwarded_to_fetcher() -> None:
    async def scenario() -> None:
        temporary = SediaHTTPError(
            "temporary",
            status_code=503,
            retryable=True,
        )
        client = FakeSediaClient(
            [
                temporary,
                {
                    "results": [
                        grant_record("A"),
                    ],
                },
            ]
        )
        store = ReadOnlySnapshotStore()
        delays: list[float] = []

        async def capture_sleep(
            delay: float,
        ) -> None:
            delays.append(delay)

        result = await run_sedia_fetch_dry_run(
            client=client,
            snapshot_store=store,  # type: ignore[arg-type]
            page_size=2,
            max_attempts=2,
            retry_delays=(0.25,),
            sleep=capture_sleep,
        )

        assert result.sync.inserted == 1
        assert len(client.requests) == 2
        assert delays == [
            0.25,
        ]
        assert store.save_calls == []

    asyncio.run(scenario())


def test_fetch_failure_stops_before_snapshot_load() -> None:
    async def scenario() -> None:
        failure = SediaHTTPError(
            "bad request",
            status_code=400,
            retryable=False,
        )
        client = FakeSediaClient(
            [
                failure,
            ]
        )
        store = ReadOnlySnapshotStore()

        with pytest.raises(
            SediaHTTPError,
            match="bad request",
        ):
            await run_sedia_fetch_dry_run(
                client=client,
                snapshot_store=store,  # type: ignore[arg-type]
                max_attempts=2,
                retry_delays=(0.1,),
                sleep=no_sleep,
            )

        assert len(client.requests) == 1
        assert store.load_calls == []
        assert store.save_calls == []

    asyncio.run(scenario())


def test_adapter_failure_never_saves_snapshot() -> None:
    async def scenario() -> None:
        client = FakeSediaClient(
            [
                {
                    "results": [
                        {
                            "reference": "A",
                        },
                    ],
                },
            ]
        )
        store = ReadOnlySnapshotStore()

        with pytest.raises(SediaAdapterError):
            await run_sedia_fetch_dry_run(
                client=client,
                snapshot_store=store,  # type: ignore[arg-type]
                page_size=2,
                sleep=no_sleep,
            )

        assert store.save_calls == []

    asyncio.run(scenario())
