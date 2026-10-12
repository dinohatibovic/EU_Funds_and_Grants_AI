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


def grant_record(
    *,
    reference: str = "TOPIC-001",
    title: str = "Structured title",
    call_title: str = "Structured call",
    status: str = "31094502",
) -> dict:
    """Return one synthetic structured grant record."""

    return {
        "reference": reference,
        "summary": "Root summary fallback",
        "content": "Structured grant description",
        "url": "https://example.invalid/topic",
        "metadata": {
            "title": [title],
            "callTitle": [call_title],
            "identifier": ["CALL-001"],
            "frameworkProgramme": ["TEST-PROGRAMME"],
            "status": [status],
            "deadlineDate": [
                "2030-12-31T17:00:00Z"
            ],
            "budget": ["1000000"],
        },
    }


def test_structured_fixture_maps_to_grant_metadata():
    payload = json.loads(
        FIXTURE_FILE.read_text(encoding="utf-8")
    )

    records = sedia_response_to_grant_metadata(
        payload
    )

    assert len(records) == 1

    metadata = records[0]

    assert metadata.id == "TEST-TOPIC-001"
    assert metadata.title == (
        "Synthetic structured grant title"
    )
    assert metadata.description == (
        "Synthetic SEDIA fixture description"
    )
    assert metadata.status == "open"
    assert metadata.deadline is not None
    assert metadata.budget == "1000000"
    assert metadata.regions == ["EU"]
    assert metadata.verified_score == 100
    assert metadata.source_priority == 100


def test_metadata_title_has_priority_over_root_summary():
    record = grant_record(
        title="Metadata title",
    )
    record["summary"] = "Root summary"

    metadata = sedia_record_to_grant_metadata(
        record
    )

    assert metadata.title == "Metadata title"
    assert metadata.description == (
        "Structured grant description"
    )


def test_call_title_is_structured_title_fallback():
    record = grant_record(
        title="",
        call_title="Call title fallback",
    )

    metadata = sedia_record_to_grant_metadata(
        record
    )

    assert metadata.title == "Call title fallback"


@pytest.mark.parametrize(
    "faq_marker",
    [
        "esST_question",
        "esST_answer",
        "esST_qaCategory",
        "esST_shortAnswer",
    ],
)
def test_faq_records_are_rejected(
    faq_marker,
):
    record = grant_record()
    record["metadata"][faq_marker] = ["FAQ value"]

    with pytest.raises(
        SediaAdapterError,
        match="FAQ metadata",
    ):
        sedia_record_to_grant_metadata(record)


@pytest.mark.parametrize(
    "missing_key",
    [
        "identifier",
        "frameworkProgramme",
        "status",
    ],
)
def test_missing_required_grant_metadata_is_rejected(
    missing_key,
):
    record = grant_record()
    del record["metadata"][missing_key]

    with pytest.raises(
        SediaAdapterError,
        match="required grant metadata",
    ):
        sedia_record_to_grant_metadata(record)


def test_missing_structured_title_is_rejected():
    record = grant_record(
        title="",
        call_title="",
    )

    with pytest.raises(
        SediaAdapterError,
        match="structured grant title",
    ):
        sedia_record_to_grant_metadata(record)


def test_missing_reference_is_rejected():
    record = grant_record()
    del record["reference"]

    with pytest.raises(
        SediaAdapterError,
        match="stable reference",
    ):
        sedia_record_to_grant_metadata(record)


def test_non_mapping_metadata_is_rejected():
    record = grant_record()
    record["metadata"] = []

    with pytest.raises(
        SediaAdapterError,
        match="metadata must be a mapping",
    ):
        sedia_record_to_grant_metadata(record)


def test_fully_invalid_deadline_is_visible():
    record = grant_record()
    record["metadata"]["deadlineDate"] = [
        "not-a-date"
    ]

    metadata = sedia_record_to_grant_metadata(
        record
    )

    assert metadata.deadline is None
    assert metadata.deadlines == []
    assert (
        metadata.deadline_validation_status
        == "fully_invalid"
    )


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
    record = grant_record(
        status=raw_status,
    )

    metadata = sedia_record_to_grant_metadata(
        record
    )

    assert metadata.status == expected


def test_unknown_status_is_preserved_normalized():
    record = grant_record(
        status="CUSTOM_STATUS",
    )

    metadata = sedia_record_to_grant_metadata(
        record
    )

    assert metadata.status == "custom_status"


def test_chroma_metadata_uses_internal_contract():
    metadata = sedia_record_to_grant_metadata(
        grant_record(reference="TOPIC-002")
    )

    chroma = metadata.to_chroma_metadata()

    assert chroma["grant_id"] == "TOPIC-002"
    assert chroma["title"] == "Structured title"
    assert chroma["status"] == "open"
    assert chroma["verified_score"] == 100


def test_embedding_text_is_deterministic():
    metadata = sedia_record_to_grant_metadata(
        grant_record(reference="TOPIC-003")
    )

    first = metadata.to_embedding_text()
    second = metadata.to_embedding_text()

    assert first == second
    assert "Structured title" in first
    assert "Structured grant description" in first
    assert "Regije: EU" in first


def test_invalid_results_shape_is_rejected():
    with pytest.raises(
        SediaAdapterError,
        match="results must be a list",
    ):
        sedia_response_to_grant_metadata(
            {"results": {}}
        )


def test_non_mapping_result_is_rejected():
    with pytest.raises(
        SediaAdapterError,
        match="Every SEDIA result must be a mapping",
    ):
        sedia_response_to_grant_metadata(
            {"results": ["invalid"]}
        )


def test_multiple_records_preserve_order():
    records = [
        grant_record(reference="TOPIC-A"),
        grant_record(reference="TOPIC-B"),
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
