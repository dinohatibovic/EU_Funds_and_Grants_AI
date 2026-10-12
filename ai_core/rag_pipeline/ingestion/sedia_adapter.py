"""Normalize validated SEDIA grant records into GrantMetadata."""

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

_FAQ_MARKERS = frozenset(
    {
        "esST_question",
        "esST_answer",
        "esST_qaCategory",
        "esST_shortAnswer",
    }
)

_REQUIRED_GRANT_METADATA = (
    "identifier",
    "frameworkProgramme",
    "status",
)


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
    """Return the first non-empty scalar or list item."""

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


def _reject_faq_record(
    metadata: Mapping[str, Any],
) -> None:
    """Reject SEDIA FAQ/search-support records."""

    present = sorted(
        marker
        for marker in _FAQ_MARKERS
        if marker in metadata
    )

    if present:
        raise SediaAdapterError(
            "SEDIA record contains FAQ metadata: "
            + ", ".join(present)
        )


def _validate_grant_metadata(
    *,
    record_id: str,
    metadata: Mapping[str, Any],
) -> None:
    """Require the structured fields of a SEDIA grant topic."""

    missing = [
        key
        for key in _REQUIRED_GRANT_METADATA
        if not _metadata_first(metadata, key)
    ]

    if missing:
        raise SediaAdapterError(
            f"SEDIA record {record_id} is missing "
            "required grant metadata: "
            + ", ".join(missing)
        )

    if not _metadata_first(
        metadata,
        "title",
        "callTitle",
    ):
        raise SediaAdapterError(
            f"SEDIA record {record_id} is missing "
            "structured grant title metadata"
        )


def _parse_deadline(value: object) -> date | None:
    """Parse one optional ISO deadline value."""

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
        except ValueError:
            return None


def _deadline_values(
    metadata: Mapping[str, Any],
) -> list:
    """Return the first present deadline field as a list."""

    for key in (
        "deadlineDate",
        "deadline",
        "submissionDeadlineDate",
        "callDeadlineDate",
    ):
        if key not in metadata:
            continue

        value = metadata.get(key)

        if value in (None, ""):
            return []

        if isinstance(value, list):
            return list(value)

        return [value]

    return []


def _normalize_deadlines(
    metadata: Mapping[str, Any],
) -> tuple[list[date], str]:
    """Normalize every valid deadline deterministically."""

    raw_values = _deadline_values(metadata)

    if not raw_values:
        return [], "no_deadline"

    parsed = [
        value
        for raw_value in raw_values
        if (value := _parse_deadline(raw_value))
        is not None
    ]

    deadlines = sorted(set(parsed))
    invalid_count = len(raw_values) - len(parsed)

    if not deadlines:
        return [], "fully_invalid"

    if invalid_count:
        return deadlines, "partially_valid"

    if len(deadlines) == 1:
        return deadlines, "single_valid"

    return deadlines, "multiple_valid"


def _normalize_status(
    metadata: Mapping[str, Any],
) -> str:
    """Normalize a required SEDIA grant status."""

    raw_status = _metadata_first(
        metadata,
        "status",
    )

    return _STATUS_MAP.get(
        raw_status.upper(),
        raw_status.lower(),
    )


def sedia_record_to_grant_metadata(
    record: Mapping[str, Any],
) -> GrantMetadata:
    """Map one validated SEDIA grant topic to GrantMetadata."""

    if not isinstance(record, Mapping):
        raise SediaAdapterError(
            "SEDIA record must be a mapping"
        )

    raw_metadata = record.get("metadata")

    if not isinstance(raw_metadata, Mapping):
        raise SediaAdapterError(
            "SEDIA metadata must be a mapping"
        )

    _reject_faq_record(raw_metadata)

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

    _validate_grant_metadata(
        record_id=record_id,
        metadata=raw_metadata,
    )

    title = _metadata_first(
        raw_metadata,
        "title",
        "callTitle",
    )

    description = _first_non_empty(
        record,
        "content",
        "description",
        "summary",
    )

    category = (
        _metadata_first(
            raw_metadata,
            "programmeTitle",
            "programme",
            "frameworkProgramme",
        )
        or "EU Funding and Tenders"
    )

    budget = _metadata_first(
        raw_metadata,
        "budget",
        "totalBudget",
    )

    deadlines, deadline_validation_status = (
        _normalize_deadlines(raw_metadata)
    )

    return GrantMetadata(
        id=record_id,
        title=title,
        description=description,
        category=category,
        budget=budget,
        note="",
        deadline=(
            deadlines[0]
            if deadlines
            else None
        ),
        deadlines=deadlines,
        deadline_validation_status=(
            deadline_validation_status
        ),
        url=_first_non_empty(record, "url"),
        relevance="high",
        status=_normalize_status(raw_metadata),
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
    """Normalize grant records while preserving order."""

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
