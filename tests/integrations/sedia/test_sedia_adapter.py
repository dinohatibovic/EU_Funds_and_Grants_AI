"""Tests for the SEDIA to GrantMetadata adapter."""

import json
from pathlib import Path

import pytest

from ai_core.rag_pipeline.ingestion.sedia_adapter import (
    SediaAdapterError,
    sedia_record_to_grant_metadata,
    sedia_records_to_grant_metadata,
    sedia_response_to_grant_metadata,
)


FIXTURE_FILE = (
    Path(__file__).resolve().parents[3]
    / "backend"
    / "app"
    / "integrations"
    / "sedia"
    / "fixtures"
    / "search_response_minimal.json"
)


def test_minimal_fixture_maps_to_grant_metadata():
    payload = json.loads(
        FIXTURE_FILE.read_text(encoding="utf-8")
    )

    records = sedia_response_to_grant_metadata(
        payload
    )

    assert len(records) == 1

    metadata = records[0]

    assert metadata.id == "TEST-TOPIC-001"
    assert metadata.title == "Synthetic SEDIA fixture"
    assert metadata.description == (
        "Synthetic SEDIA fixture"
    )
    assert metadata.status == "open"
    assert metadata.regions == ["EU"]
    assert metadata.beneficiary_types == [
        "general"
    ]
    assert metadata.verified_score == 100
    assert metadata.source_priority == 100


def test_chroma_metadata_uses_internal_contract():
    record = {
        "reference": "TOPIC-002",
        "summary": "Digital Europe call",
        "url": "https://example.eu/topic/2",
        "metadata": {
            "status": ["OPEN"],
        },
    }

    metadata = sedia_record_to_grant_metadata(
        record
    )

    chroma = metadata.to_chroma_metadata()

    assert chroma["grant_id"] == "TOPIC-002"
    assert chroma["title"] == "Digital Europe call"
    assert chroma["status"] == "open"
    assert chroma["url"] == (
        "https://example.eu/topic/2"
    )


def test_embedding_text_is_deterministic():
    record = {
        "reference": "TOPIC-003",
        "summary": "SME digitalisation",
        "content": "Support for small enterprises",
        "metadata": {
            "status": ["31094502"],
        },
    }

    metadata = sedia_record_to_grant_metadata(
        record
    )

    first = metadata.to_embedding_text()
    second = metadata.to_embedding_text()

    assert first == second
    assert "SME digitalisation" in first
    assert "Support for small enterprises" in first
    assert "Regije: EU" in first


@pytest.mark.parametrize(
    ("raw_status", "expected"),
    [
        ("31094501", "forthcoming"),
        ("31094502", "open"),
        ("31094503", "closed"),
        ("OPEN", "open"),
        ("CLOSED", "closed"),
    ],
)
def test_known_status_values_are_normalized(
    raw_status,
    expected,
):
    record = {
        "reference": "TOPIC-STATUS",
        "summary": "Status mapping",
        "metadata": {
            "status": [raw_status],
        },
    }

    metadata = sedia_record_to_grant_metadata(
        record
    )

    assert metadata.status == expected


def test_missing_status_requires_review():
    record = {
        "reference": "TOPIC-004",
        "summary": "Missing status",
    }

    metadata = sedia_record_to_grant_metadata(
        record
    )

    assert metadata.status == "needs_review"


def test_missing_reference_is_rejected():
    record = {
        "summary": "No stable identifier",
    }

    with pytest.raises(
        SediaAdapterError,
        match="stable reference",
    ):
        sedia_record_to_grant_metadata(record)


def test_missing_title_is_rejected():
    record = {
        "reference": "TOPIC-005",
    }

    with pytest.raises(
        SediaAdapterError,
        match="missing a title",
    ):
        sedia_record_to_grant_metadata(record)


def test_invalid_deadline_is_rejected():
    record = {
        "reference": "TOPIC-006",
        "summary": "Invalid deadline",
        "deadline": "not-a-date",
    }

    with pytest.raises(
        SediaAdapterError,
        match="Invalid SEDIA deadline",
    ):
        sedia_record_to_grant_metadata(record)


def test_invalid_results_shape_is_rejected():
    with pytest.raises(
        SediaAdapterError,
        match="results must be a list",
    ):
        sedia_response_to_grant_metadata(
            {"results": {}}
        )


def test_multiple_records_preserve_order():
    records = [
        {
            "reference": "TOPIC-A",
            "summary": "A",
        },
        {
            "reference": "TOPIC-B",
            "summary": "B",
        },
    ]

    normalized = (
        sedia_records_to_grant_metadata(
            records
        )
    )

    assert [
        record.id
        for record in normalized
    ] == [
        "TOPIC-A",
        "TOPIC-B",
    ]
