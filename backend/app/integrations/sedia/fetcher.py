"""Read-only paginated fetching for the public SEDIA API."""

from __future__ import annotations

import asyncio
from collections.abc import (
    Awaitable,
    Callable,
    Mapping,
    Sequence,
)
from dataclasses import dataclass
from typing import Any, Protocol

from .exceptions import SediaHTTPError
from .models import (
    SediaSearchRequest,
    SediaSearchResponse,
)


class SediaSearchClient(Protocol):
    """Minimal client contract required by the fetcher."""

    async def search(
        self,
        request: SediaSearchRequest,
    ) -> SediaSearchResponse:
        """Return one validated SEDIA response page."""


RetryablePredicate = Callable[[Exception], bool]
SleepCallable = Callable[[float], Awaitable[None]]


def is_retryable_sedia_error(
    exc: Exception,
) -> bool:
    """Return whether a SEDIA exception is safe to retry."""

    return (
        isinstance(exc, SediaHTTPError)
        and exc.retryable
    )


class SediaFetchError(RuntimeError):
    """Raised when paginated fetching cannot finish safely."""


@dataclass(frozen=True)
class SediaFetchResult:
    """Stable result of one read-only paginated fetch."""

    payload: dict[str, Any]
    pages_fetched: int
    records_fetched: int


def _page_results(
    response: SediaSearchResponse,
) -> tuple[dict[str, Any], ...]:
    """Validate and return records from one response page."""

    results = response.raw.get("results")

    if not isinstance(results, list):
        raise SediaFetchError(
            "SEDIA response must contain a results list"
        )

    validated: list[dict[str, Any]] = []

    for index, record in enumerate(results):
        if not isinstance(record, Mapping):
            raise SediaFetchError(
                "SEDIA result at index "
                f"{index} must be an object"
            )

        validated.append(dict(record))

    return tuple(validated)


def _stable_record_id(
    record: Mapping[str, Any],
) -> str | None:
    """Return an available stable record identifier."""

    for key in (
        "reference",
        "id",
        "topicId",
    ):
        value = record.get(key)

        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _reject_duplicate_ids(
    records: Sequence[Mapping[str, Any]],
    seen_ids: set[str],
) -> None:
    """Reject duplicate stable IDs across fetched pages."""

    for record in records:
        record_id = _stable_record_id(record)

        if record_id is None:
            continue

        if record_id in seen_ids:
            raise SediaFetchError(
                "duplicate SEDIA record id across pages: "
                f"{record_id}"
            )

        seen_ids.add(record_id)


async def _search_with_retry(
    *,
    client: SediaSearchClient,
    request: SediaSearchRequest,
    max_attempts: int,
    retry_delays: Sequence[float],
    retryable: RetryablePredicate,
    sleep: SleepCallable,
) -> SediaSearchResponse:
    """Search one page with bounded, explicit retry behavior."""

    for attempt in range(1, max_attempts + 1):
        try:
            return await client.search(request)
        except Exception as exc:
            if not retryable(exc) or attempt >= max_attempts:
                raise

            delay = retry_delays[attempt - 1]
            await sleep(delay)

    raise AssertionError("unreachable retry state")


async def fetch_sedia_pages(
    *,
    client: SediaSearchClient,
    text: str = "",
    filters: Mapping[str, Any] | None = None,
    page_size: int = 100,
    max_pages: int = 100,
    max_attempts: int = 1,
    retry_delays: Sequence[float] = (1.0, 2.0),
    retryable: RetryablePredicate = (
        is_retryable_sedia_error
    ),
    sleep: SleepCallable = asyncio.sleep,
) -> SediaFetchResult:
    """Fetch consecutive SEDIA pages without writing data.

    Pagination stops after the first short page. ``max_pages``
    prevents an unbounded loop when every response page is full.
    """

    if page_size < 1 or page_size > 100:
        raise ValueError(
            "page_size must be between 1 and 100"
        )

    if max_pages < 1:
        raise ValueError(
            "max_pages must be positive"
        )

    if max_attempts < 1:
        raise ValueError(
            "max_attempts must be positive"
        )

    required_delays = max_attempts - 1

    if len(retry_delays) < required_delays:
        raise ValueError(
            "retry_delays must cover every retry"
        )

    if any(delay < 0 for delay in retry_delays):
        raise ValueError(
            "retry delays cannot be negative"
        )

    normalized_filters = dict(
        filters or {}
    )
    aggregated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for page_number in range(
        1,
        max_pages + 1,
    ):
        request = SediaSearchRequest(
            text=text,
            page_number=page_number,
            page_size=page_size,
            filters=normalized_filters,
        )

        response = await _search_with_retry(
            client=client,
            request=request,
            max_attempts=max_attempts,
            retry_delays=retry_delays,
            retryable=retryable,
            sleep=sleep,
        )

        page_records = _page_results(
            response
        )

        _reject_duplicate_ids(
            page_records,
            seen_ids,
        )

        aggregated.extend(
            page_records
        )

        if len(page_records) < page_size:
            return SediaFetchResult(
                payload={
                    "results": aggregated,
                },
                pages_fetched=page_number,
                records_fetched=len(aggregated),
            )

    raise SediaFetchError(
        "SEDIA pagination reached max_pages "
        "without a short final page"
    )
