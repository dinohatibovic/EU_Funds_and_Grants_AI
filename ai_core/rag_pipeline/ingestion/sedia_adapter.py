"""Normalize SEDIA search records into the GrantMetadata contract."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime
from typing import Any

from ai_core.rag_pipeline.grant_metadata import GrantMetadata


class SediaAdapterError(ValueError):
    """Raised when a SEDIA record cannot be normalized safely."""


_STATUS_MAP = {
    "31094501": "forthcoming",
    "31094502": "open",
    "31094503": "closed",
    "FORTHCOMING": "forthcoming",
    "OPEN": "open",
    "CLOSED": "closed",
}


def _clean_string(value: object) -> str:
    """Return a stripped string without converting None to 'None'."""

    if value is None:
        return ""

    return str(value).strip()


def _first_non_empty(
    record: Mapping[str, Any],
    *keys: str,
) -> str:
    """Return the first non-empty scalar from candidate keys."""

    for key in keys:
        value = _clean_string(record.get(key))

        if value:
            return value

    return ""


def _metadata_first(
    metadata: Mapping[str, Any],
    *keys: str,
) -> str:
    """Return the first non-empty SEDIA metadata value."""

    for key in keys:
        value = metadata.get(key)

        if isinstance(value, list):
            for item in value:
                cleaned = _clean_string(item)

                if cleaned:
                    return cleaned

            continue

        cleaned = _clean_string(value)

        if cleaned:
            return cleaned

    return ""


def _parse_deadline(value: object) -> date | None:
    """Parse an optional ISO date without inventing missing values."""

    if value in (None, ""):
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = _clean_string(value)

    if not text:
        return None

    normalized = text.replace("Z", "+00:00")

    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError as exc:
            raise SediaAdapterError(
                f"Invalid SEDIA deadline: {text}"
            ) from exc


def _normalize_status(
    record: Mapping[str, Any],
    metadata: Mapping[str, Any],
) -> str:
    """Normalize known SEDIA status values."""

    raw_status = (
        _metadata_first(
            metadata,
            "status",
            "statusCode",
            "topicStatus",
        )
        or _first_non_empty(
            record,
            "status",
            "statusCode",
        )
    )

    if not raw_status:
        return "needs_review"

    return _STATUS_MAP.get(
        raw_status.upper(),
        raw_status.lower(),
    )


def sedia_record_to_grant_metadata(
    record: Mapping[str, Any],
) -> GrantMetadata:
    """Map one SEDIA search result to GrantMetadata."""

    if not isinstance(record, Mapping):
        raise SediaAdapterError(
            "SEDIA record must be a mapping"
        )

    raw_metadata = record.get("metadata", {})

    if raw_metadata is None:
        raw_metadata = {}

    if not isinstance(raw_metadata, Mapping):
        raise SediaAdapterError(
            "SEDIA metadata must be a mapping"
        )

    record_id = _first_non_empty(
        record,
        "reference",
        "id",
        "topicId",
        "topic_id",
        "callId",
    )

    if not record_id:
        raise SediaAdapterError(
            "SEDIA record is missing a stable reference"
        )

    title = _first_non_empty(
        record,
        "title",
        "summary",
        "content",
        "name",
    )

    if not title:
        raise SediaAdapterError(
            f"SEDIA record {record_id} is missing a title"
        )

    description = _first_non_empty(
        record,
        "content",
        "description",
        "summary",
    )

    category = (
        _first_non_empty(
            record,
            "programme",
            "programmeName",
            "category",
        )
        or _metadata_first(
            raw_metadata,
            "programmeTitle",
            "programme",
            "frameworkProgramme",
        )
        or "EU Funding and Tenders"
    )

    budget = (
        _first_non_empty(
            record,
            "budget",
            "totalBudget",
        )
        or _metadata_first(
            raw_metadata,
            "budget",
            "totalBudget",
        )
    )

    deadline_value: object = (
        record.get("deadline")
        or _metadata_first(
            raw_metadata,
            "deadline",
            "deadlineDate",
            "submissionDeadlineDate",
            "callDeadlineDate",
        )
    )

    return GrantMetadata(
        id=record_id,
        title=title,
        description=description,
        category=category,
        budget=budget,
        note="",
        deadline=_parse_deadline(deadline_value),
        url=_first_non_empty(record, "url"),
        relevance="high",
        status=_normalize_status(
            record,
            raw_metadata,
        ),
        verified_score=100,
        source_priority=100,
        regions=["EU"],
        beneficiary_types=["general"],
        sectors=[],
        next_expected=None,
    )


def sedia_records_to_grant_metadata(
    records: Iterable[Mapping[str, Any]],
) -> list:
    """Normalize multiple SEDIA records while preserving order."""

    return [
        sedia_record_to_grant_metadata(record)
        for record in records
    ]


def sedia_response_to_grant_metadata(
    payload: Mapping[str, Any],
) -> list:
    """Normalize the results array from one SEDIA response."""

    if not isinstance(payload, Mapping):
        raise SediaAdapterError(
            "SEDIA response must be a mapping"
        )

    results = payload.get("results")

    if not isinstance(results, list):
        raise SediaAdapterError(
            "SEDIA response results must be a list"
        )

    normalized_records: list[Mapping[str, Any]] = []

    for record in results:
        if not isinstance(record, Mapping):
            raise SediaAdapterError(
                "Every SEDIA result must be a mapping"
            )

        normalized_records.append(record)

    return sedia_records_to_grant_metadata(
        normalized_records
    )
