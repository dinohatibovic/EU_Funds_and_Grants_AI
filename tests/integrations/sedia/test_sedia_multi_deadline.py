"""Regression tests for the SEDIA multi-deadline contract."""

from datetime import date

from ai_core.rag_pipeline.grant_metadata import (
    GrantMetadata,
)
from ai_core.rag_pipeline.ingestion.sedia_adapter import (
    sedia_record_to_grant_metadata,
)
from ai_core.rag_pipeline.ingestion.sync_planner import (
    stable_grant_hash,
)


def grant_record(deadline_value=...):
    metadata = {
        "title": ["Synthetic grant"],
        "callTitle": ["Synthetic call"],
        "identifier": ["CALL-MULTI-001"],
        "frameworkProgramme": ["TEST"],
        "status": ["OPEN"],
    }

    if deadline_value is not ...:
        metadata["deadlineDate"] = deadline_value

    return {
        "reference": "TOPIC-MULTI-001",
        "content": "Synthetic description",
        "url": "https://example.invalid/multi",
        "metadata": metadata,
    }


def test_no_deadline_is_visible():
    grant = sedia_record_to_grant_metadata(
        grant_record()
    )

    assert grant.deadline is None
    assert grant.deadlines == []
    assert (
        grant.deadline_validation_status
        == "no_deadline"
    )


def test_single_valid_deadline_is_preserved():
    grant = sedia_record_to_grant_metadata(
        grant_record(
            ["2030-12-31T17:00:00Z"]
        )
    )

    assert grant.deadline == date(2030, 12, 31)
    assert grant.deadlines == [
        date(2030, 12, 31)
    ]
    assert (
        grant.deadline_validation_status
        == "single_valid"
    )


def test_multiple_valid_deadlines_are_sorted():
    grant = sedia_record_to_grant_metadata(
        grant_record(
            [
                "2031-06-30T17:00:00Z",
                "2030-12-31T17:00:00Z",
            ]
        )
    )

    assert grant.deadline == date(2030, 12, 31)
    assert grant.deadlines == [
        date(2030, 12, 31),
        date(2031, 6, 30),
    ]
    assert (
        grant.deadline_validation_status
        == "multiple_valid"
    )


def test_partial_invalid_deadline_is_tolerated():
    grant = sedia_record_to_grant_metadata(
        grant_record(
            [
                "not-a-date",
                "2030-12-31T17:00:00Z",
            ]
        )
    )

    assert grant.deadline == date(2030, 12, 31)
    assert grant.deadlines == [
        date(2030, 12, 31)
    ]
    assert (
        grant.deadline_validation_status
        == "partially_valid"
    )


def test_fully_invalid_deadline_is_visible():
    grant = sedia_record_to_grant_metadata(
        grant_record(
            [
                "not-a-date",
                object(),
            ]
        )
    )

    assert grant.deadline is None
    assert grant.deadlines == []
    assert (
        grant.deadline_validation_status
        == "fully_invalid"
    )


def test_duplicate_deadlines_are_deduplicated():
    grant = sedia_record_to_grant_metadata(
        grant_record(
            [
                "2030-12-31",
                "2030-12-31T17:00:00Z",
            ]
        )
    )

    assert grant.deadlines == [
        date(2030, 12, 31)
    ]
    assert (
        grant.deadline_validation_status
        == "single_valid"
    )


def test_scalar_deadline_fallback_is_supported():
    grant = sedia_record_to_grant_metadata(
        grant_record("2030-12-31")
    )

    assert grant.deadline == date(2030, 12, 31)
    assert grant.deadlines == [
        date(2030, 12, 31)
    ]


def make_metadata(deadlines):
    return GrantMetadata(
        id="hash-test",
        title="Hash test",
        description="Synthetic",
        category="Test",
        budget="",
        note="",
        deadline=None,
        deadlines=deadlines,
        deadline_validation_status="multiple_valid",
        url="https://example.invalid/hash",
        relevance="high",
        status="open",
        verified_score=100,
        source_priority=100,
        regions=["EU"],
        beneficiary_types=["general"],
        sectors=[],
        next_expected=None,
    )


def test_hash_is_stable_for_deadline_order():
    first = make_metadata(
        ["2031-06-30", "2030-12-31"]
    )
    second = make_metadata(
        ["2030-12-31", "2031-06-30"]
    )

    assert first.deadlines == second.deadlines
    assert stable_grant_hash(
        first
    ) == stable_grant_hash(
        second
    )


def test_hash_changes_with_deadline_set():
    first = make_metadata(
        ["2030-12-31", "2031-06-30"]
    )
    second = make_metadata(
        ["2030-12-31", "2032-06-30"]
    )

    assert stable_grant_hash(
        first
    ) != stable_grant_hash(
        second
    )


def test_chroma_validation_status_is_visible():
    grant = sedia_record_to_grant_metadata(
        grant_record(
            [
                "invalid",
                "2030-12-31",
            ]
        )
    )

    chroma = grant.to_chroma_metadata()

    assert (
        chroma["deadline_validation_status"]
        == "partially_valid"
    )
    assert chroma["deadlines"] == '["2030-12-31"]'
