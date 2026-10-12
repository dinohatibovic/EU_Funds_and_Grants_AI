"""Async HTTP client for the public SEDIA API."""

from __future__ import annotations

import json
from typing import Any, Self

import httpx

from .config import SediaSettings
from .exceptions import (
    SediaHTTPError,
    SediaResponseError,
)
from .models import (
    SediaSearchRequest,
    SediaSearchResponse,
)


class SediaClient:
    """Transport-only client for the SEDIA Search API."""

    def __init__(
        self,
        settings: SediaSettings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings or SediaSettings()
        self._client = httpx.AsyncClient(
            timeout=self.settings.timeout_seconds,
            transport=transport,
            headers={
                "Accept": (
                    "application/json, text/plain, */*"
                ),
                "User-Agent": self.settings.user_agent,
                "Origin": self.settings.origin,
                "Referer": self.settings.referer,
            },
        )

    async def __aenter__(self) -> Self:
        """Enter the asynchronous context."""

        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        """Close the HTTP client on context exit."""

        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTPX client."""

        await self._client.aclose()

    async def search(
        self,
        request: SediaSearchRequest,
    ) -> SediaSearchResponse:
        """Execute one validated SEDIA search request."""

        query_json = json.dumps(
            request.to_query_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        languages_json = json.dumps(
            list(request.languages),
            ensure_ascii=False,
            separators=(",", ":"),
        )

        files = {
            "query": (
                None,
                query_json,
                "application/json",
            ),
            "languages": (
                None,
                languages_json,
                "application/json",
            ),
            "displayLanguage": (
                None,
                request.display_language,
                "text/plain",
            ),
        }

        try:
            response = await self._client.post(
                self.settings.search_url,
                params=request.to_url_params(
                    api_key=self.settings.api_key,
                ),
                files=files,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            retryable = (
                status_code == 429
                or 500 <= status_code <= 599
            )

            raise SediaHTTPError(
                "SEDIA request failed with HTTP "
                f"{status_code}",
                status_code=status_code,
                retryable=retryable,
            ) from exc
        except httpx.RequestError as exc:
            raise SediaHTTPError(
                "SEDIA transport failed: "
                f"{exc.__class__.__name__}",
                retryable=True,
            ) from exc
        except httpx.HTTPError as exc:
            raise SediaHTTPError(
                "SEDIA request failed: "
                f"{exc.__class__.__name__}",
                retryable=False,
            ) from exc

        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise SediaResponseError(
                "SEDIA response is not valid JSON"
            ) from exc

        try:
            return SediaSearchResponse.from_payload(
                payload
            )
        except (TypeError, ValueError) as exc:
            raise SediaResponseError(
                "SEDIA response violates the "
                "expected root contract"
            ) from exc
