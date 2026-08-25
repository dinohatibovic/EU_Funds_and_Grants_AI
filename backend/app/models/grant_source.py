"""Validated source-registry model."""

from __future__ import annotations

from enum import IntEnum

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class SourceAuthorityLevel(IntEnum):
    """Authority assigned to a grant source."""

    OFFICIAL_PUBLISHER = 1
    OFFICIAL_PROGRAMME_PORTAL = 2
    VERIFIED_AGGREGATOR = 3
    UNVERIFIED_INFORMATIONAL = 4


class GrantSource(BaseModel):
    """Canonical configuration for one grant source."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    source_id: str = Field(
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9_]+$",
    )
    name: str = Field(
        min_length=2,
        max_length=200,
    )
    base_url: AnyHttpUrl
    source_type: str = Field(
        min_length=2,
        max_length=100,
    )
    authority_level: SourceAuthorityLevel
    jurisdiction: str = Field(
        min_length=2,
        max_length=150,
    )
    access_method: str = Field(
        min_length=2,
        max_length=100,
    )
    content_scope: tuple[str, ...] = Field(
        min_length=1,
    )
    enabled: bool = True
    requires_manual_review: bool = True

    @field_validator("content_scope")
    @classmethod
    def validate_content_scope(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Reject blank or duplicate scope values."""

        normalized = tuple(
            item.strip()
            for item in value
        )

        if any(not item for item in normalized):
            raise ValueError(
                "Content scope cannot contain "
                "empty values"
            )

        if len(normalized) != len(set(normalized)):
            raise ValueError(
                "Content scope contains duplicates"
            )

        return normalized
