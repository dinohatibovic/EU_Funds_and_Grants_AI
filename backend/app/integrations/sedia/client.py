"""Async HTTP client for the public SEDIA API."""

from __future__ import annotations

import json
from typing import Any

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
                "Accept": "application/json",
                "User-Agent": self.settings.user_agent,
            },
        )

    async def __aenter__(self) -> "SediaClient":
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
            request.to_api_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        try:
            response = await self._client.post(
                self.settings.search_url,
                params={
                    "apiKey": self.settings.api_key,
                },
                data={
                    "query": query_json,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SediaHTTPError(
                "SEDIA request failed: "
                f"{exc.__class__.__name__}"
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
