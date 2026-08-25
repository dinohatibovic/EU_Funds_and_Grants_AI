"""Configuration contract for the SEDIA API."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SediaSettings:
    """Immutable configuration for the SEDIA client."""

    search_url: str = (
        "https://api.tech.ec.europa.eu/"
        "search-api/prod/rest/search"
    )
    facet_url: str = (
        "https://api.tech.ec.europa.eu/"
        "search-api/prod/rest/facet"
    )
    api_key: str = "SEDIA"
    timeout_seconds: float = 30.0
    user_agent: str = "FinAssistBH-SEDIA/1.0"

    def __post_init__(self) -> None:
        if not self.search_url.startswith("https://"):
            raise ValueError(
                "SEDIA search URL must use HTTPS"
            )

        if not self.facet_url.startswith("https://"):
            raise ValueError(
                "SEDIA facet URL must use HTTPS"
            )

        if not self.api_key.strip():
            raise ValueError(
                "SEDIA API identifier cannot be empty"
            )

        if self.timeout_seconds <= 0:
            raise ValueError(
                "SEDIA timeout must be positive"
            )

        if not self.user_agent.strip():
            raise ValueError(
                "SEDIA user agent cannot be empty"
            )
