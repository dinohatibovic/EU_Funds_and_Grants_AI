import asyncio
import json
from pathlib import Path

import httpx
import pytest

from backend.app.integrations.sedia import (
    SediaClient,
    SediaHTTPError,
    SediaResponseError,
    SediaSearchRequest,
    SediaSettings,
)


def test_sedia_settings_use_https() -> None:
    settings = SediaSettings()

    assert settings.search_url.startswith("https://")
    assert settings.facet_url.startswith("https://")
    assert settings.api_key == "SEDIA"


def test_request_rejects_invalid_page_size() -> None:
    with pytest.raises(ValueError):
        SediaSearchRequest(page_size=101)


def test_client_sends_validated_request() -> None:
    async def scenario() -> None:
        def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            assert request.method == "POST"
            assert request.url.params["apiKey"] == (
                "SEDIA"
            )
            assert b"query=" in request.content

            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "reference": "TEST-001"
                        }
                    ]
                },
            )

        transport = httpx.MockTransport(handler)

        async with SediaClient(
            transport=transport
        ) as client:
            response = await client.search(
                SediaSearchRequest(
                    text="digital",
                    page_number=1,
                    page_size=10,
                )
            )

        assert response.raw["results"][0][
            "reference"
        ] == "TEST-001"

    asyncio.run(scenario())


def test_client_rejects_non_json() -> None:
    async def scenario() -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                text="not-json",
                headers={
                    "Content-Type": "text/plain"
                },
            )
        )

        async with SediaClient(
            transport=transport
        ) as client:
            with pytest.raises(SediaResponseError):
                await client.search(
                    SediaSearchRequest()
                )

    asyncio.run(scenario())


def test_client_wraps_http_errors() -> None:
    async def scenario() -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(503)
        )

        async with SediaClient(
            transport=transport
        ) as client:
            with pytest.raises(SediaHTTPError):
                await client.search(
                    SediaSearchRequest()
                )

    asyncio.run(scenario())


def test_fixture_is_valid_json() -> None:
    fixture = Path(
        "backend/app/integrations/sedia/"
        "fixtures/search_response_minimal.json"
    )

    payload = json.loads(
        fixture.read_text(encoding="utf-8")
    )

    assert payload["results"][0]["reference"] == (
        "TEST-TOPIC-001"
    )
