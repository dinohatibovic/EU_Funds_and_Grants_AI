"""Regression tests for totalResults-aware SEDIA pagination."""

import asyncio
from collections.abc import Sequence

import pytest

from backend.app.integrations.sedia.fetcher import (
    SediaFetchError,
    fetch_sedia_pages,
)
from backend.app.integrations.sedia.models import (
    SediaSearchRequest,
    SediaSearchResponse,
)


class FakeClient:
    def __init__(
        self,
        payloads: Sequence[dict[str, object]],
    ) -> None:
        self.payloads = list(payloads)
        self.requests: list[SediaSearchRequest] = []

    async def search(
        self,
        request: SediaSearchRequest,
    ) -> SediaSearchResponse:
        self.requests.append(request)
        index = len(self.requests) - 1

        if index >= len(self.payloads):
            raise AssertionError(
                "unexpected extra SEDIA request"
            )

        return SediaSearchResponse.from_payload(
            self.payloads[index]
        )


def record(reference: str) -> dict[str, object]:
    return {
        "reference": reference,
        "summary": f"Grant {reference}",
    }


def run_fetch(
    payloads: Sequence[dict[str, object]],
    *,
    page_size: int = 2,
    max_pages: int = 100,
):
    async def scenario():
        client = FakeClient(payloads)
        result = await fetch_sedia_pages(
            client=client,
            page_size=page_size,
            max_pages=max_pages,
        )
        return client, result

    return asyncio.run(scenario())


def test_total_reached_on_full_page_stops_without_extra_request():
    client, result = run_fetch(
        [
            {
                "totalResults": 2,
                "results": [
                    record("A"),
                    record("B"),
                ],
            },
        ],
        page_size=2,
    )

    assert len(client.requests) == 1
    assert result.pages_fetched == 1
    assert result.records_fetched == 2
    assert result.reported_total == 2
    assert result.unique_records == 2
    assert (
        result.termination_reason
        == "reported_total_reached"
    )


def test_total_reached_across_multiple_pages():
    client, result = run_fetch(
        [
            {
                "totalResults": 3,
                "results": [
                    record("A"),
                    record("B"),
                ],
            },
            {
                "totalResults": 3,
                "results": [
                    record("C"),
                ],
            },
        ],
    )

    assert len(client.requests) == 2
    assert result.records_fetched == 3
    assert result.reported_total == 3
    assert result.unique_records == 3
    assert (
        result.termination_reason
        == "reported_total_reached"
    )


def test_missing_total_preserves_short_page_fallback():
    _, result = run_fetch(
        [
            {
                "results": [
                    record("A"),
                ],
            },
        ],
    )

    assert result.reported_total is None
    assert result.unique_records == 1
    assert result.termination_reason == "short_page"


def test_empty_first_page_without_total_is_valid():
    _, result = run_fetch(
        [
            {
                "results": [],
            },
        ],
    )

    assert result.records_fetched == 0
    assert result.reported_total is None
    assert result.unique_records == 0
    assert (
        result.termination_reason
        == "empty_first_page"
    )


def test_zero_total_with_empty_first_page_is_valid():
    _, result = run_fetch(
        [
            {
                "totalResults": 0,
                "results": [],
            },
        ],
    )

    assert result.records_fetched == 0
    assert result.reported_total == 0
    assert result.unique_records == 0
    assert (
        result.termination_reason
        == "empty_first_page"
    )


@pytest.mark.parametrize(
    "invalid_total",
    [
        -1,
        True,
        False,
        1.5,
        "2",
        None,
        [],
        {},
    ],
)
def test_invalid_total_results_is_rejected(
    invalid_total,
):
    with pytest.raises(
        SediaFetchError,
        match="non-negative integer",
    ):
        run_fetch(
            [
                {
                    "totalResults": invalid_total,
                    "results": [],
                },
            ]
        )


def test_total_results_change_is_rejected():
    with pytest.raises(
        SediaFetchError,
        match="changed between pages",
    ):
        run_fetch(
            [
                {
                    "totalResults": 3,
                    "results": [
                        record("A"),
                        record("B"),
                    ],
                },
                {
                    "totalResults": 4,
                    "results": [
                        record("C"),
                    ],
                },
            ]
        )


def test_total_presence_change_is_rejected():
    with pytest.raises(
        SediaFetchError,
        match="changed between pages",
    ):
        run_fetch(
            [
                {
                    "results": [
                        record("A"),
                        record("B"),
                    ],
                },
                {
                    "totalResults": 3,
                    "results": [
                        record("C"),
                    ],
                },
            ]
        )


def test_empty_intermediate_page_is_rejected():
    with pytest.raises(
        SediaFetchError,
        match="empty SEDIA page",
    ):
        run_fetch(
            [
                {
                    "totalResults": 3,
                    "results": [
                        record("A"),
                        record("B"),
                    ],
                },
                {
                    "totalResults": 3,
                    "results": [],
                },
            ]
        )


def test_records_exceed_total_is_rejected():
    with pytest.raises(
        SediaFetchError,
        match="exceed totalResults",
    ):
        run_fetch(
            [
                {
                    "totalResults": 1,
                    "results": [
                        record("A"),
                        record("B"),
                    ],
                },
            ]
        )


def test_short_page_before_total_is_rejected():
    with pytest.raises(
        SediaFetchError,
        match="short SEDIA page",
    ):
        run_fetch(
            [
                {
                    "totalResults": 3,
                    "results": [
                        record("A"),
                    ],
                },
            ],
            page_size=2,
        )


def test_duplicate_id_guard_remains_active():
    with pytest.raises(
        SediaFetchError,
        match="duplicate SEDIA record id",
    ):
        run_fetch(
            [
                {
                    "totalResults": 3,
                    "results": [
                        record("A"),
                        record("B"),
                    ],
                },
                {
                    "totalResults": 3,
                    "results": [
                        record("B"),
                    ],
                },
            ]
        )


def test_max_pages_guard_remains_active():
    with pytest.raises(
        SediaFetchError,
        match="reached max_pages",
    ):
        run_fetch(
            [
                {
                    "results": [
                        record("A"),
                    ],
                },
                {
                    "results": [
                        record("B"),
                    ],
                },
            ],
            page_size=1,
            max_pages=2,
        )
