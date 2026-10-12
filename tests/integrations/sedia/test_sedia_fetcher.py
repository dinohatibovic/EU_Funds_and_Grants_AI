import asyncio
from collections.abc import Sequence

import pytest

from backend.app.integrations.sedia.exceptions import (
    SediaHTTPError,
    SediaResponseError,
)
from backend.app.integrations.sedia.fetcher import (
    SediaFetchError,
    fetch_sedia_pages,
)
from backend.app.integrations.sedia.models import (
    SediaSearchRequest,
    SediaSearchResponse,
)


class FakeSediaClient:
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


def record(
    reference: str,
) -> dict[str, object]:
    return {
        "reference": reference,
        "summary": f"Grant {reference}",
    }


def test_single_short_page_stops_fetch() -> None:
    async def scenario() -> None:
        client = FakeSediaClient(
            [
                {
                    "results": [
                        record("A"),
                    ],
                },
            ]
        )

        result = await fetch_sedia_pages(
            client=client,
            page_size=2,
        )

        assert result.pages_fetched == 1
        assert result.records_fetched == 1
        assert result.payload["results"] == [
            record("A"),
        ]
        assert [
            request.page_number
            for request in client.requests
        ] == [1]

    asyncio.run(scenario())


def test_two_pages_are_aggregated_in_order() -> None:
    async def scenario() -> None:
        client = FakeSediaClient(
            [
                {
                    "results": [
                        record("A"),
                        record("B"),
                    ],
                },
                {
                    "results": [
                        record("C"),
                    ],
                },
            ]
        )

        result = await fetch_sedia_pages(
            client=client,
            text="digital",
            page_size=2,
        )

        assert result.pages_fetched == 2
        assert result.records_fetched == 3
        assert [
            item["reference"]
            for item in result.payload["results"]
        ] == [
            "A",
            "B",
            "C",
        ]
        assert [
            request.page_number
            for request in client.requests
        ] == [
            1,
            2,
        ]

    asyncio.run(scenario())


def test_empty_first_page_returns_empty_payload() -> None:
    async def scenario() -> None:
        client = FakeSediaClient(
            [
                {
                    "results": [],
                },
            ]
        )

        result = await fetch_sedia_pages(
            client=client,
            page_size=10,
        )

        assert result.pages_fetched == 1
        assert result.records_fetched == 0
        assert result.payload == {
            "results": [],
        }

    asyncio.run(scenario())


def test_duplicate_id_across_pages_is_rejected() -> None:
    async def scenario() -> None:
        client = FakeSediaClient(
            [
                {
                    "results": [
                        record("A"),
                        record("B"),
                    ],
                },
                {
                    "results": [
                        record("B"),
                    ],
                },
            ]
        )

        with pytest.raises(
            SediaFetchError,
            match="duplicate SEDIA record id",
        ):
            await fetch_sedia_pages(
                client=client,
                page_size=2,
            )

    asyncio.run(scenario())


def test_max_pages_guard_rejects_full_final_page() -> None:
    async def scenario() -> None:
        client = FakeSediaClient(
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
            ]
        )

        with pytest.raises(
            SediaFetchError,
            match="reached max_pages",
        ):
            await fetch_sedia_pages(
                client=client,
                page_size=1,
                max_pages=2,
            )

    asyncio.run(scenario())


def test_request_contract_is_preserved() -> None:
    async def scenario() -> None:
        client = FakeSediaClient(
            [
                {
                    "results": [
                        record("A"),
                    ],
                },
                {
                    "results": [],
                },
            ]
        )

        await fetch_sedia_pages(
            client=client,
            text="renewable energy",
            filters={
                "status": "OPEN",
            },
            page_size=1,
        )

        assert len(client.requests) == 2

        for request in client.requests:
            assert request.text == (
                "renewable energy"
            )
            assert request.filters == {
                "status": "OPEN",
            }
            assert request.page_size == 1

    asyncio.run(scenario())


def test_results_must_be_a_list() -> None:
    async def scenario() -> None:
        client = FakeSediaClient(
            [
                {
                    "results": {
                        "reference": "A",
                    },
                },
            ]
        )

        with pytest.raises(
            SediaFetchError,
            match="results list",
        ):
            await fetch_sedia_pages(
                client=client,
            )

    asyncio.run(scenario())


class ScriptedSediaClient:
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
            raise AssertionError(
                "scripted outcome must be a dict or exception"
            )

        return SediaSearchResponse.from_payload(
            outcome
        )


def test_retry_succeeds_after_transient_error() -> None:
    async def scenario() -> None:
        transient = RuntimeError(
            "temporary"
        )
        client = ScriptedSediaClient(
            [
                transient,
                {
                    "results": [
                        record("A"),
                    ],
                },
            ]
        )
        delays: list[float] = []

        async def fake_sleep(
            delay: float,
        ) -> None:
            delays.append(delay)

        result = await fetch_sedia_pages(
            client=client,
            page_size=2,
            max_attempts=2,
            retry_delays=(0.25,),
            retryable=lambda exc: exc is transient,
            sleep=fake_sleep,
        )

        assert result.records_fetched == 1
        assert len(client.requests) == 2
        assert delays == [0.25]
        assert client.requests[0] == client.requests[1]

    asyncio.run(scenario())


def test_retry_exhaustion_reraises_last_error() -> None:
    async def scenario() -> None:
        first = RuntimeError("first")
        second = RuntimeError("second")
        client = ScriptedSediaClient(
            [
                first,
                second,
            ]
        )
        delays: list[float] = []

        async def fake_sleep(
            delay: float,
        ) -> None:
            delays.append(delay)

        with pytest.raises(
            RuntimeError,
            match="second",
        ):
            await fetch_sedia_pages(
                client=client,
                max_attempts=2,
                retry_delays=(0.5,),
                retryable=lambda exc: isinstance(
                    exc,
                    RuntimeError,
                ),
                sleep=fake_sleep,
            )

        assert len(client.requests) == 2
        assert delays == [0.5]

    asyncio.run(scenario())


def test_non_retryable_error_is_not_repeated() -> None:
    async def scenario() -> None:
        permanent = ValueError(
            "permanent"
        )
        client = ScriptedSediaClient(
            [
                permanent,
            ]
        )
        delays: list[float] = []

        async def fake_sleep(
            delay: float,
        ) -> None:
            delays.append(delay)

        with pytest.raises(
            ValueError,
            match="permanent",
        ):
            await fetch_sedia_pages(
                client=client,
                max_attempts=3,
                retry_delays=(0.1, 0.2),
                retryable=lambda exc: False,
                sleep=fake_sleep,
            )

        assert len(client.requests) == 1
        assert delays == []

    asyncio.run(scenario())


def test_retry_delay_contract_is_validated() -> None:
    async def scenario() -> None:
        client = ScriptedSediaClient([])

        with pytest.raises(
            ValueError,
            match="cover every retry",
        ):
            await fetch_sedia_pages(
                client=client,
                max_attempts=3,
                retry_delays=(0.1,),
            )

        with pytest.raises(
            ValueError,
            match="cannot be negative",
        ):
            await fetch_sedia_pages(
                client=client,
                retry_delays=(-1.0,),
            )

        assert client.requests == []

    asyncio.run(scenario())


def test_default_policy_retries_retryable_sedia_error() -> None:
    async def scenario() -> None:
        transient = SediaHTTPError(
            "temporary",
            status_code=503,
            retryable=True,
        )
        client = ScriptedSediaClient(
            [
                transient,
                {
                    "results": [
                        record("A"),
                    ],
                },
            ]
        )
        delays: list[float] = []

        async def fake_sleep(
            delay: float,
        ) -> None:
            delays.append(delay)

        result = await fetch_sedia_pages(
            client=client,
            page_size=2,
            max_attempts=2,
            retry_delays=(0.2,),
            sleep=fake_sleep,
        )

        assert result.records_fetched == 1
        assert len(client.requests) == 2
        assert delays == [0.2]

    asyncio.run(scenario())


def test_default_policy_does_not_retry_permanent_http_error() -> None:
    async def scenario() -> None:
        permanent = SediaHTTPError(
            "bad request",
            status_code=400,
            retryable=False,
        )
        client = ScriptedSediaClient(
            [
                permanent,
            ]
        )
        delays: list[float] = []

        async def fake_sleep(
            delay: float,
        ) -> None:
            delays.append(delay)

        with pytest.raises(
            SediaHTTPError,
            match="bad request",
        ):
            await fetch_sedia_pages(
                client=client,
                max_attempts=3,
                retry_delays=(0.1, 0.2),
                sleep=fake_sleep,
            )

        assert len(client.requests) == 1
        assert delays == []

    asyncio.run(scenario())


def test_default_policy_does_not_retry_response_error() -> None:
    async def scenario() -> None:
        invalid = SediaResponseError(
            "invalid response"
        )
        client = ScriptedSediaClient(
            [
                invalid,
            ]
        )
        delays: list[float] = []

        async def fake_sleep(
            delay: float,
        ) -> None:
            delays.append(delay)

        with pytest.raises(
            SediaResponseError,
            match="invalid response",
        ):
            await fetch_sedia_pages(
                client=client,
                max_attempts=3,
                retry_delays=(0.1, 0.2),
                sleep=fake_sleep,
            )

        assert len(client.requests) == 1
        assert delays == []

    asyncio.run(scenario())


def test_default_policy_reraises_last_retryable_error() -> None:
    async def scenario() -> None:
        first = SediaHTTPError(
            "first",
            status_code=503,
            retryable=True,
        )
        second = SediaHTTPError(
            "second",
            status_code=503,
            retryable=True,
        )
        client = ScriptedSediaClient(
            [
                first,
                second,
            ]
        )
        delays: list[float] = []

        async def fake_sleep(
            delay: float,
        ) -> None:
            delays.append(delay)

        with pytest.raises(
            SediaHTTPError,
            match="second",
        ) as captured:
            await fetch_sedia_pages(
                client=client,
                max_attempts=2,
                retry_delays=(0.4,),
                sleep=fake_sleep,
            )

        assert captured.value is second
        assert len(client.requests) == 2
        assert delays == [0.4]

    asyncio.run(scenario())
