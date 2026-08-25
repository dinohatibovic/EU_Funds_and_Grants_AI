"""Transport models for SEDIA requests and responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SediaSearchRequest(BaseModel):
    """Validated request for the SEDIA Search API."""

    model_config = ConfigDict(extra="forbid")

    text: str = ""
    page_number: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    filters: dict[str, Any] = Field(
        default_factory=dict
    )

    def to_api_payload(self) -> dict[str, Any]:
        """Return a stable internal request payload."""

        return {
            "text": self.text,
            "pageNumber": self.page_number,
            "pageSize": self.page_size,
            "filters": self.filters,
        }


class SediaSearchResponse(BaseModel):
    """Minimal wrapper before normalization."""

    model_config = ConfigDict(extra="forbid")

    raw: dict[str, Any]

    @classmethod
    def from_payload(
        cls,
        payload: object,
    ) -> "SediaSearchResponse":
        """Validate the root response type."""

        if not isinstance(payload, dict):
            raise TypeError(
                "SEDIA response must be a JSON object"
            )

        return cls(raw=payload)
