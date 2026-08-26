"""Tests for deterministic grant hashing and incremental sync planning."""

from __future__ import annotations

from copy import deepcopy

import pytest

from ai_core.rag_pipeline.grant_metadata import GrantMetadata
from ai_core.rag_pipeline.ingestion.sync_planner import (
    SyncAction,
    SyncPlannerError,
    build_hash_snapshot,
    canonical_grant_payload,
    plan_incremental_sync,
    stable_grant_hash,
    validate_hash_snapshot,
)


def make_grant(
    grant_id="grant-a",
    title="Digital Europe",
    description="Support for SMEs",
    regions=None,
    beneficiary_types=None,
    sectors=None,
):
    """Build one valid GrantMetadata test record."""

    return GrantMetadata(
        id=grant_id,
        title=title,
        description=description,
        category="Digital",
        budget="1000000 EUR",
        note="",
        deadline="2027-01-31",
        url="https://example.eu/grants/a",
        relevance="high",
        status="open",
        verified_score=100,
        source_priority=100,
        regions=regions or [
            "EU",
            "Montenegro",
        ],
        beneficiary_types=beneficiary_types or [
            "SME",
            "Startup",
        ],
        sectors=sectors or [
            "digitalization",
            "innovation",
        ],
        next_expected=None,
    )


def test_hash_is_deterministic():
    grant = make_grant()

    first = stable_grant_hash(grant)
    second = stable_grant_hash(grant)

    assert first == second
    assert len(first) == 64
    assert set(first) <= set(
        "0123456789abcdef"
    )


def test_hash_changes_when_content_changes():
    original = make_grant()
    changed = make_grant(
        description="Changed description"
    )

    assert stable_grant_hash(
        original
    ) != stable_grant_hash(
        changed
    )


def test_hash_ignores_order_of_semantic_lists():
    first = make_grant(
        regions=["EU", "Montenegro"],
        beneficiary_types=["SME", "Startup"],
        sectors=["innovation", "digitalization"],
    )

    second = make_grant(
        regions=["Montenegro", "EU"],
        beneficiary_types=["Startup", "SME"],
        sectors=["digitalization", "innovation"],
    )

    assert stable_grant_hash(first) == stable_grant_hash(
        second
    )


def test_canonical_payload_does_not_mutate_model():
    grant = make_grant(
        sectors=["innovation", "digitalization"]
    )

    original = deepcopy(grant.model_dump())
    payload = canonical_grant_payload(grant)

    assert grant.model_dump() == original
    assert payload["sectors"] == [
        "digitalization",
        "innovation",
    ]


def test_snapshot_contains_each_grant_hash():
    first = make_grant(
        grant_id="grant-a"
    )
    second = make_grant(
        grant_id="grant-b",
        title="Horizon Europe",
    )

    snapshot = build_hash_snapshot(
        [first, second]
    )

    assert snapshot == {
        "grant-a": stable_grant_hash(first),
        "grant-b": stable_grant_hash(second),
    }


def test_snapshot_rejects_duplicate_ids():
    first = make_grant()
    duplicate = make_grant(
        title="Different title"
    )

    with pytest.raises(
        SyncPlannerError,
        match="duplicate grant id",
    ):
        build_hash_snapshot(
            [first, duplicate]
        )


def test_new_grant_is_planned_as_insert():
    grant = make_grant()

    plan = plan_incremental_sync(
        [grant],
        {},
    )

    assert len(plan.items) == 1
    assert plan.items[0].action is SyncAction.INSERT
    assert plan.items[0].grant_id == grant.id
    assert plan.counts == {
        "insert": 1,
        "update": 0,
        "skip": 0,
        "total": 1,
    }


def test_unchanged_grant_is_planned_as_skip():
    grant = make_grant()

    plan = plan_incremental_sync(
        [grant],
        build_hash_snapshot([grant]),
    )

    assert plan.items[0].action is SyncAction.SKIP
    assert plan.skips == plan.items
    assert plan.counts["skip"] == 1


def test_changed_grant_is_planned_as_update():
    original = make_grant()
    changed = make_grant(
        description="Updated description"
    )

    plan = plan_incremental_sync(
        [changed],
        build_hash_snapshot([original]),
    )

    assert plan.items[0].action is SyncAction.UPDATE
    assert plan.updates == plan.items
    assert plan.counts["update"] == 1


def test_mixed_plan_preserves_input_order():
    unchanged = make_grant(
        grant_id="grant-a",
    )
    original_changed = make_grant(
        grant_id="grant-b",
        title="Old title",
    )
    changed = make_grant(
        grant_id="grant-b",
        title="New title",
    )
    inserted = make_grant(
        grant_id="grant-c",
    )

    previous = build_hash_snapshot(
        [
            unchanged,
            original_changed,
        ]
    )

    plan = plan_incremental_sync(
        [
            unchanged,
            changed,
            inserted,
        ],
        previous,
    )

    assert [
        item.grant_id
        for item in plan.items
    ] == [
        "grant-a",
        "grant-b",
        "grant-c",
    ]

    assert [
        item.action
        for item in plan.items
    ] == [
        SyncAction.SKIP,
        SyncAction.UPDATE,
        SyncAction.INSERT,
    ]

    assert plan.counts == {
        "insert": 1,
        "update": 1,
        "skip": 1,
        "total": 3,
    }


def test_empty_input_produces_empty_plan():
    plan = plan_incremental_sync(
        [],
        {},
    )

    assert plan.items == ()
    assert plan.inserts == ()
    assert plan.updates == ()
    assert plan.skips == ()
    assert plan.counts == {
        "insert": 0,
        "update": 0,
        "skip": 0,
        "total": 0,
    }


def test_planner_rejects_duplicate_current_ids():
    first = make_grant()
    duplicate = make_grant(
        title="Duplicate"
    )

    with pytest.raises(
        SyncPlannerError,
        match="duplicate grant id",
    ):
        plan_incremental_sync(
            [first, duplicate],
            {},
        )


@pytest.mark.parametrize(
    "snapshot",
    [
        {"": "a" * 64},
        {" grant-a": "a" * 64},
        {"grant-a": ""},
        {"grant-a": "not-a-hash"},
        {"grant-a": "g" * 64},
        {"grant-a": 123},
    ],
)
def test_invalid_snapshots_are_rejected(snapshot):
    with pytest.raises(SyncPlannerError):
        validate_hash_snapshot(snapshot)


def test_uppercase_snapshot_hash_is_normalized():
    grant = make_grant()
    content_hash = stable_grant_hash(grant)

    validated = validate_hash_snapshot(
        {
            grant.id: content_hash.upper(),
        }
    )

    assert validated == {
        grant.id: content_hash,
    }


def test_non_metadata_input_is_rejected():
    with pytest.raises(
        SyncPlannerError,
        match="GrantMetadata",
    ):
        stable_grant_hash(
            {"id": "not-a-model"}
        )

    with pytest.raises(
        SyncPlannerError,
        match="GrantMetadata",
    ):
        plan_incremental_sync(
            [{"id": "not-a-model"}],
            {},
        )
