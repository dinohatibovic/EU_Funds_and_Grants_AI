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


@pytest.mark.parametrize(
    ("status_code", "retryable"),
    [
        (400, False),
        (401, False),
        (403, False),
        (404, False),
        (429, True),
        (500, True),
        (503, True),
        (599, True),
    ],
)
def test_client_classifies_http_status(
    status_code: int,
    retryable: bool,
) -> None:
    async def scenario() -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                status_code,
            )
        )

        async with SediaClient(
            transport=transport
        ) as client:
            with pytest.raises(
                SediaHTTPError
            ) as captured:
                await client.search(
                    SediaSearchRequest()
                )

        error = captured.value

        assert error.status_code == status_code
        assert error.retryable is retryable
        assert f"HTTP {status_code}" in str(error)

    asyncio.run(scenario())


def test_client_marks_timeout_as_retryable() -> None:
    async def scenario() -> None:
        def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            raise httpx.ReadTimeout(
                "timed out",
                request=request,
            )

        transport = httpx.MockTransport(
            handler
        )

        async with SediaClient(
            transport=transport
        ) as client:
            with pytest.raises(
                SediaHTTPError
            ) as captured:
                await client.search(
                    SediaSearchRequest()
                )

        error = captured.value

        assert error.status_code is None
        assert error.retryable is True
        assert "ReadTimeout" in str(error)

    asyncio.run(scenario())


def test_client_marks_connection_error_as_retryable() -> None:
    async def scenario() -> None:
        def handler(
            request: httpx.Request,
        ) -> httpx.Response:
            raise httpx.ConnectError(
                "connection failed",
                request=request,
            )

        transport = httpx.MockTransport(
            handler
        )

        async with SediaClient(
            transport=transport
        ) as client:
            with pytest.raises(
                SediaHTTPError
            ) as captured:
                await client.search(
                    SediaSearchRequest()
                )

        error = captured.value

        assert error.status_code is None
        assert error.retryable is True
        assert "ConnectError" in str(error)

    asyncio.run(scenario())
