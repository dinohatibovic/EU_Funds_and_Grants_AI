"""Tests for the shared grant metadata contract."""

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_core.rag_pipeline.grant_metadata import (
    build_chroma_metadata,
    build_embedding_text,
    validate_grant_record,
)


GRANTS_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "grants.json"
)


@pytest.fixture(scope="module")
def grants():
    return json.loads(
        GRANTS_FILE.read_text(encoding="utf-8")
    )


def test_all_dataset_records_match_contract(grants):
    validated = [
        validate_grant_record(record)
        for record in grants
    ]

    assert len(validated) == 30
    assert all(record.id for record in validated)
    assert all(record.title for record in validated)


def test_deadline_is_parsed_as_date(grants):
    record = next(
        item
        for item in grants
        if item["deadline"] is not None
    )

    assert isinstance(
        validate_grant_record(record).deadline,
        date,
    )


def test_empty_sectors_are_allowed(grants):
    record = next(
        item
        for item in grants
        if not item["sectors"]
    )

    assert validate_grant_record(record).sectors == []


@pytest.mark.parametrize(
    "field",
    [
        "regions",
        "beneficiary_types",
    ],
)
def test_required_lists_must_not_be_empty(grants, field):
    record = dict(grants[0])
    record[field] = []

    with pytest.raises(ValidationError):
        validate_grant_record(record)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("verified_score", -1),
        ("verified_score", 101),
        ("source_priority", -1),
        ("source_priority", 101),
    ],
)
def test_ranking_scores_use_zero_to_100_range(
    grants,
    field,
    value,
):
    record = dict(grants[0])
    record[field] = value

    with pytest.raises(ValidationError):
        validate_grant_record(record)


def test_chroma_metadata_contains_scalars_only(grants):
    metadata = build_chroma_metadata(grants[0])

    assert metadata["grant_id"] == grants[0]["id"]
    assert isinstance(metadata["verified_score"], int)
    assert isinstance(metadata["source_priority"], int)
    assert isinstance(metadata["regions"], str)
    assert isinstance(metadata["beneficiary_types"], str)
    assert isinstance(metadata["sectors"], str)
    assert all(value is not None for value in metadata.values())


def test_list_metadata_uses_compact_json(grants):
    metadata = build_chroma_metadata(grants[0])

    assert json.loads(metadata["regions"]) == grants[0]["regions"]
    assert (
        json.loads(metadata["beneficiary_types"])
        == grants[0]["beneficiary_types"]
    )
    assert json.loads(metadata["sectors"]) == grants[0]["sectors"]


def test_embedding_text_is_deterministic(grants):
    first = build_embedding_text(grants[0])
    second = build_embedding_text(grants[0])

    assert first == second
    assert grants[0]["title"] in first
    assert "Kategorija:" in first
    assert "Rok:" in first
    assert "Budžet:" in first


def test_list_values_are_trimmed_and_deduplicated(grants):
    record = dict(grants[0])
    record["sectors"] = [
        " digitalization ",
        "digitalization",
        "",
    ]

    validated = validate_grant_record(record)

    assert validated.sectors == ["digitalization"]
