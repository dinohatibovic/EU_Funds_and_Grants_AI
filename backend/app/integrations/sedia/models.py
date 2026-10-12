"""Transport models for SEDIA requests and responses."""

from __future__ import annotations

from typing import Any, Literal

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
    sort_by: str = "deadline"
    order_by: Literal["ASC", "DESC"] = "ASC"
    languages: tuple[str, ...] = ("en",)
    display_language: str = "en"

    def to_query_payload(self) -> dict[str, Any]:
        """Return the Elasticsearch-style multipart query."""

        if self.filters:
            return dict(self.filters)

        return {
            "bool": {
                "must": [],
            },
        }

    def to_url_params(
        self,
        *,
        api_key: str,
    ) -> dict[str, str]:
        """Return transport values expected as URL parameters."""

        return {
            "apiKey": api_key,
            "text": self.text,
            "pageSize": str(self.page_size),
            "pageNumber": str(self.page_number),
            "sortBy": self.sort_by,
            "orderBy": self.order_by,
        }


class SediaSearchResponse(BaseModel):
    """Minimal wrapper before normalization."""

    model_config = ConfigDict(extra="forbid")

    raw: dict[str, Any]

    @classmethod
    def from_payload(
        cls,
        payload: object,
    ) -> SediaSearchResponse:
        """Validate the root response type."""

        if not isinstance(payload, dict):
            raise TypeError(
                "SEDIA response must be a JSON object"
            )

        return cls(raw=payload)
