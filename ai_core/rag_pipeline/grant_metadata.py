"""Structured metadata contract for grant records stored in ChromaDB."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


def _serialize_list(values: list[str]) -> str:
    return json.dumps(
        values,
        ensure_ascii=False,
        separators=(",", ":"),
    )


class GrantMetadata(BaseModel):
    """Validated grant metadata shared by ingestion paths."""

    model_config = ConfigDict(
        extra="ignore",
        str_strip_whitespace=True,
    )

    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = ""
    category: str = ""
    budget: str = ""
    note: str = ""
    deadline: date | None = None
    deadlines: list[date] = Field(
        default_factory=list
    )
    deadline_validation_status: str = (
        "no_deadline"
    )
    url: str = ""
    relevance: str = ""
    status: str = Field(min_length=1)

    verified_score: int = Field(ge=0, le=100)
    source_priority: int = Field(ge=0, le=100)

    regions: list[str] = Field(min_length=1)
    beneficiary_types: list[str] = Field(min_length=1)
    sectors: list[str] = Field(default_factory=list)

    next_expected: str | None = None

    @field_validator(
        "deadlines",
        mode="before",
    )
    @classmethod
    def normalize_deadlines(
        cls,
        value: Any,
    ) -> list[date]:
        if value is None:
            return []

        if not isinstance(value, list):
            raise TypeError(
                "deadlines mora biti lista datuma"
            )

        normalized = {
            item
            if isinstance(item, date)
            else date.fromisoformat(str(item))
            for item in value
        }

        return sorted(normalized)

    @model_validator(mode="after")
    def align_primary_deadline(
        self,
    ) -> GrantMetadata:
        if self.deadlines:
            primary = self.deadlines[0]

            if self.deadline != primary:
                self.deadline = primary
        elif self.deadline is not None:
            self.deadlines = [self.deadline]

            if (
                self.deadline_validation_status
                == "no_deadline"
            ):
                self.deadline_validation_status = (
                    "single_valid"
                )

        return self

    @field_validator(
        "regions",
        "beneficiary_types",
        "sectors",
        mode="before",
    )
    @classmethod
    def normalize_string_list(
        cls,
        value: Any,
    ) -> list[str]:
        if value is None:
            return []

        if not isinstance(value, list):
            raise ValueError(
                "vrijednost mora biti lista stringova"
            )

        normalized: list[str] = []
        seen: set[str] = set()

        for item in value:
            if not isinstance(item, str):
                raise ValueError(
                    "sve vrijednosti liste moraju biti stringovi"
                )

            cleaned = item.strip()

            if not cleaned or cleaned in seen:
                continue

            seen.add(cleaned)
            normalized.append(cleaned)

        return normalized

    def to_embedding_text(self) -> str:
        """Build one deterministic embedding text for all ingestion paths."""
        parts = [
            self.title,
            f"Kategorija: {self.category}",
            self.description,
            (
                f"Rok: {self.deadline.isoformat()}"
                if self.deadline
                else "Rok: nije naveden"
            ),
            f"Budžet: {self.budget or 'nije naveden'}",
        ]

        if self.note:
            parts.append(f"Napomena: {self.note}")

        if self.sectors:
            parts.append(
                "Sektori: " + ", ".join(self.sectors)
            )

        if self.regions:
            parts.append(
                "Regije: " + ", ".join(self.regions)
            )

        if self.beneficiary_types:
            parts.append(
                "Korisnici: "
                + ", ".join(self.beneficiary_types)
            )

        if self.url:
            parts.append(f"Izvor: {self.url}")

        return ". ".join(
            part
            for part in parts
            if part.strip()
        )

    def to_chroma_metadata(
        self,
    ) -> dict[str, str | int]:
        return {
            "grant_id": self.id,
            "title": self.title,
            "category": self.category,
            "budget": self.budget,
            "deadline": (
                self.deadline.isoformat()
                if self.deadline
                else ""
            ),
            "deadlines": _serialize_list(
                [
                    value.isoformat()
                    for value in self.deadlines
                ]
            ),
            "deadline_validation_status": (
                self.deadline_validation_status
            ),
            "url": self.url,
            "relevance": self.relevance,
            "status": self.status,
            "verified_score": self.verified_score,
            "source_priority": self.source_priority,
            "regions": _serialize_list(self.regions),
            "beneficiary_types": _serialize_list(
                self.beneficiary_types
            ),
            "sectors": _serialize_list(self.sectors),
            "next_expected": self.next_expected or "",
        }


def validate_grant_record(
    record: dict[str, Any],
) -> GrantMetadata:
    """Validate one complete grants.json record."""
    return GrantMetadata.model_validate(record)


def build_chroma_metadata(
    record: dict[str, Any],
) -> dict[str, str | int]:
    """Validate and serialize a record for ChromaDB."""
    return validate_grant_record(
        record
    ).to_chroma_metadata()


def build_embedding_text(
    record: dict[str, Any],
) -> str:
    """Validate a record and build its shared embedding text."""
    return validate_grant_record(
        record
    ).to_embedding_text()
