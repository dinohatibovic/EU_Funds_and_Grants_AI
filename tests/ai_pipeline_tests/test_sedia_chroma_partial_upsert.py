"""Tests for the pure SEDIA Chroma partial-upsert plan."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ai_core.rag_pipeline.grant_metadata import (
    GrantMetadata,
)
from ai_core.rag_pipeline.ingestion.sedia_chroma_partial_upsert import (
    SediaChromaPartialUpsertError,
    build_chroma_partial_upsert_plan,
)
from ai_core.rag_pipeline.ingestion.sedia_controlled_apply import (
    SediaApplyMutation,
    build_apply_context,
)


def _grant(
    grant_id: str,
    title: str,
) -> GrantMetadata:
    return GrantMetadata(
        id=grant_id,
        title=title,
        description=f"Description for {title}",
        category="Digital",
        budget="100000 EUR",
        deadline="2027-01-31",
        deadlines=[
            "2027-01-31",
        ],
        deadline_validation_status=(
            "single_valid"
        ),
        url=(
            "https://example.test/"
            + grant_id
        ),
        relevance="high",
        status="open",
        verified_score=90,
        source_priority=95,
        regions=[
            "Bosnia and Herzegovina",
        ],
        beneficiary_types=[
            "SME",
        ],
        sectors=[
            "Digital",
        ],
    )


def _fixture():
    new_grant = _grant(
        "grant-new",
        "New Grant",
    )
    existing_grant = _grant(
        "grant-existing",
        "Existing Grant Updated",
    )

    context = build_apply_context(
        source_id="eu_sedia",
        previous_hashes={
            "grant-existing": "a" * 64,
        },
        target_hashes={
            "grant-new": "b" * 64,
            "grant-existing": "c" * 64,
        },
        expected_insert_count=1,
        expected_update_count=1,
        changed_grant_ids=(
            "grant-new",
            "grant-existing",
        ),
        mutations=(
            SediaApplyMutation(
                grant_id="grant-new",
                action="insert",
            ),
            SediaApplyMutation(
                grant_id="grant-existing",
                action="update",
            ),
        ),
    )

    embeddings = (
        (0.1, 0.2, 0.3),
        (0.4, 0.5, 0.6),
    )

    return (
        (new_grant, existing_grant),
        context,
        embeddings,
    )


def test_plan_is_deterministic_and_action_aware():
    grants, context, embeddings = (
        _fixture()
    )

    first = build_chroma_partial_upsert_plan(
        grants=grants,
        context=context,
        embeddings=embeddings,
    )
    second = build_chroma_partial_upsert_plan(
        grants=grants,
        context=context,
        embeddings=embeddings,
    )

    assert first == second
    assert first.run_id == context.run_id
    assert first.transaction_id.startswith(
        "chroma-partial:"
    )
    assert first.grant_ids == (
        "grant-new",
        "grant-existing",
    )
    assert first.insert_ids == (
        "grant-new",
    )
    assert first.update_ids == (
        "grant-existing",
    )
    assert first.embedding_dimension == 3


def test_plan_uses_shared_document_and_metadata_contract():
    grants, context, embeddings = (
        _fixture()
    )

    plan = build_chroma_partial_upsert_plan(
        grants=grants,
        context=context,
        embeddings=embeddings,
    )

    first = plan.records[0]

    assert first.document == (
        grants[0].to_embedding_text()
    )
    assert first.metadata_dict == (
        grants[0].to_chroma_metadata()
    )
    assert (
        first.metadata_dict["grant_id"]
        == first.grant_id
    )


def test_plan_and_records_are_immutable():
    grants, context, embeddings = (
        _fixture()
    )

    plan = build_chroma_partial_upsert_plan(
        grants=grants,
        context=context,
        embeddings=embeddings,
    )

    with pytest.raises(
        FrozenInstanceError,
    ):
        plan.embedding_dimension = 20

    with pytest.raises(
        FrozenInstanceError,
    ):
        plan.records[0].action = "update"


def test_metadata_copy_cannot_mutate_prepared_record():
    grants, context, embeddings = (
        _fixture()
    )

    plan = build_chroma_partial_upsert_plan(
        grants=grants,
        context=context,
        embeddings=embeddings,
    )

    metadata = (
        plan.records[0].metadata_dict
    )
    metadata["title"] = "Changed outside"

    assert (
        plan.records[0].metadata_dict[
            "title"
        ]
        == "New Grant"
    )


def test_action_change_changes_transaction_id():
    grants, context, embeddings = (
        _fixture()
    )

    first = build_chroma_partial_upsert_plan(
        grants=grants,
        context=context,
        embeddings=embeddings,
    )

    changed_context = build_apply_context(
        source_id="eu_sedia",
        previous_hashes={
            "grant-new": "d" * 64,
        },
        target_hashes={
            "grant-new": "b" * 64,
            "grant-existing": "c" * 64,
        },
        expected_insert_count=1,
        expected_update_count=1,
        changed_grant_ids=(
            "grant-new",
            "grant-existing",
        ),
        mutations=(
            SediaApplyMutation(
                grant_id="grant-new",
                action="update",
            ),
            SediaApplyMutation(
                grant_id="grant-existing",
                action="insert",
            ),
        ),
    )

    second = build_chroma_partial_upsert_plan(
        grants=grants,
        context=changed_context,
        embeddings=embeddings,
    )

    assert first.transaction_id != (
        second.transaction_id
    )


def test_embedding_change_changes_transaction_id():
    grants, context, embeddings = (
        _fixture()
    )

    first = build_chroma_partial_upsert_plan(
        grants=grants,
        context=context,
        embeddings=embeddings,
    )

    second = build_chroma_partial_upsert_plan(
        grants=grants,
        context=context,
        embeddings=(
            (0.1, 0.2, 0.9),
            embeddings[1],
        ),
    )

    assert first.transaction_id != (
        second.transaction_id
    )


def test_plan_requires_action_aware_mutations():
    grants, _, embeddings = _fixture()

    context = build_apply_context(
        source_id="eu_sedia",
        previous_hashes={},
        target_hashes={
            "grant-new": "b" * 64,
            "grant-existing": "c" * 64,
        },
        expected_insert_count=2,
        expected_update_count=0,
        changed_grant_ids=(
            "grant-new",
            "grant-existing",
        ),
    )

    with pytest.raises(
        SediaChromaPartialUpsertError,
        match="mutations are required",
    ):
        build_chroma_partial_upsert_plan(
            grants=grants,
            context=context,
            embeddings=embeddings,
        )


def test_plan_rejects_reordered_grants():
    grants, context, embeddings = (
        _fixture()
    )

    with pytest.raises(
        SediaChromaPartialUpsertError,
        match="same order",
    ):
        build_chroma_partial_upsert_plan(
            grants=tuple(reversed(grants)),
            context=context,
            embeddings=embeddings,
        )


def test_plan_rejects_embedding_count_mismatch():
    grants, context, embeddings = (
        _fixture()
    )

    with pytest.raises(
        SediaChromaPartialUpsertError,
        match="embedding count",
    ):
        build_chroma_partial_upsert_plan(
            grants=grants,
            context=context,
            embeddings=embeddings[:1],
        )


@pytest.mark.parametrize(
    "invalid_embedding, message",
    [
        (
            (),
            "cannot be empty",
        ),
        (
            (0.1, "bad", 0.3),
            "non-numeric",
        ),
        (
            (0.1, float("nan"), 0.3),
            "non-finite",
        ),
        (
            (0.1, float("inf"), 0.3),
            "non-finite",
        ),
        (
            (0.1, True, 0.3),
            "non-numeric",
        ),
    ],
)
def test_plan_rejects_invalid_embeddings(
    invalid_embedding,
    message,
):
    grants, context, embeddings = (
        _fixture()
    )

    with pytest.raises(
        SediaChromaPartialUpsertError,
        match=message,
    ):
        build_chroma_partial_upsert_plan(
            grants=grants,
            context=context,
            embeddings=(
                invalid_embedding,
                embeddings[1],
            ),
        )


def test_plan_rejects_mixed_embedding_dimensions():
    grants, context, embeddings = (
        _fixture()
    )

    with pytest.raises(
        SediaChromaPartialUpsertError,
        match="same dimension",
    ):
        build_chroma_partial_upsert_plan(
            grants=grants,
            context=context,
            embeddings=(
                embeddings[0],
                (0.4, 0.5),
            ),
        )


def test_plan_does_not_mutate_inputs():
    grants, context, embeddings = (
        _fixture()
    )

    grant_ids_before = tuple(
        grant.id
        for grant in grants
    )
    embeddings_before = tuple(
        tuple(vector)
        for vector in embeddings
    )

    build_chroma_partial_upsert_plan(
        grants=grants,
        context=context,
        embeddings=embeddings,
    )

    assert tuple(
        grant.id
        for grant in grants
    ) == grant_ids_before

    assert embeddings == embeddings_before

def _stored_record(
    grant_id: str,
    *,
    marker: float,
):
    from ai_core.rag_pipeline.ingestion.sedia_chroma_partial_upsert import (
        SediaChromaStoredRecord,
    )

    return SediaChromaStoredRecord(
        grant_id=grant_id,
        document=f"Document {grant_id}",
        metadata=(
            ("grant_id", grant_id),
            ("status", "open"),
        ),
        embedding=(
            marker,
            marker + 0.1,
        ),
    )


def test_fixture_collection_snapshot_is_deterministic():
    from ai_core.rag_pipeline.ingestion.sedia_chroma_partial_upsert import (
        SediaChromaFixtureCollection,
    )

    collection = SediaChromaFixtureCollection(
        records=(
            _stored_record(
                "grant-b",
                marker=0.2,
            ),
            _stored_record(
                "grant-a",
                marker=0.1,
            ),
        )
    )

    assert tuple(
        record.grant_id
        for record in collection.snapshot()
    ) == (
        "grant-a",
        "grant-b",
    )


def test_fixture_collection_get_preserves_requested_order():
    from ai_core.rag_pipeline.ingestion.sedia_chroma_partial_upsert import (
        SediaChromaFixtureCollection,
    )

    collection = SediaChromaFixtureCollection(
        records=(
            _stored_record(
                "grant-a",
                marker=0.1,
            ),
            _stored_record(
                "grant-b",
                marker=0.2,
            ),
        )
    )

    records = collection.get_by_ids(
        (
            "grant-b",
            "missing",
            "grant-a",
        )
    )

    assert tuple(
        record.grant_id
        for record in records
    ) == (
        "grant-b",
        "grant-a",
    )
    assert collection.get_calls == [
        (
            "grant-b",
            "missing",
            "grant-a",
        )
    ]


def test_fixture_collection_upserts_only_exact_records():
    from ai_core.rag_pipeline.ingestion.sedia_chroma_partial_upsert import (
        SediaChromaFixtureCollection,
    )

    old = _stored_record(
        "grant-existing",
        marker=0.1,
    )
    untouched = _stored_record(
        "grant-untouched",
        marker=0.2,
    )
    updated = _stored_record(
        "grant-existing",
        marker=0.8,
    )
    inserted = _stored_record(
        "grant-new",
        marker=0.9,
    )

    collection = SediaChromaFixtureCollection(
        records=(
            old,
            untouched,
        )
    )

    applied = collection.upsert_exact(
        (
            updated,
            inserted,
        )
    )

    assert applied == (
        "grant-existing",
        "grant-new",
    )
    assert collection.upsert_calls == [
        (
            "grant-existing",
            "grant-new",
        )
    ]

    snapshot = {
        record.grant_id: record
        for record in collection.snapshot()
    }

    assert snapshot[
        "grant-existing"
    ] == updated
    assert snapshot[
        "grant-new"
    ] == inserted
    assert snapshot[
        "grant-untouched"
    ] == untouched


def test_fixture_collection_delete_is_exact_and_non_destructive():
    from ai_core.rag_pipeline.ingestion.sedia_chroma_partial_upsert import (
        SediaChromaFixtureCollection,
    )

    first = _stored_record(
        "grant-a",
        marker=0.1,
    )
    second = _stored_record(
        "grant-b",
        marker=0.2,
    )

    collection = SediaChromaFixtureCollection(
        records=(
            first,
            second,
        )
    )

    deleted = collection.delete_exact(
        (
            "missing",
            "grant-a",
        )
    )

    assert deleted == (
        "grant-a",
    )
    assert collection.delete_calls == [
        (
            "missing",
            "grant-a",
        )
    ]
    assert collection.snapshot() == (
        second,
    )


def test_fixture_collection_partial_upsert_failure_is_visible():
    from ai_core.rag_pipeline.ingestion.sedia_chroma_partial_upsert import (
        SediaChromaFixtureCollection,
        SediaChromaFixtureCollectionError,
    )

    first = _stored_record(
        "grant-a",
        marker=0.1,
    )
    second = _stored_record(
        "grant-b",
        marker=0.2,
    )

    collection = SediaChromaFixtureCollection(
        fail_upsert_after=1,
    )

    with pytest.raises(
        SediaChromaFixtureCollectionError,
        match="after 1 records",
    ):
        collection.upsert_exact(
            (
                first,
                second,
            )
        )

    assert collection.snapshot() == (
        first,
    )


def test_fixture_collection_partial_delete_failure_is_visible():
    from ai_core.rag_pipeline.ingestion.sedia_chroma_partial_upsert import (
        SediaChromaFixtureCollection,
        SediaChromaFixtureCollectionError,
    )

    first = _stored_record(
        "grant-a",
        marker=0.1,
    )
    second = _stored_record(
        "grant-b",
        marker=0.2,
    )

    collection = SediaChromaFixtureCollection(
        records=(
            first,
            second,
        ),
        fail_delete_after=1,
    )

    with pytest.raises(
        SediaChromaFixtureCollectionError,
        match="after 1 records",
    ):
        collection.delete_exact(
            (
                "grant-a",
                "grant-b",
            )
        )

    assert collection.snapshot() == (
        second,
    )


@pytest.mark.parametrize(
    "method_name, values",
    [
        (
            "get_by_ids",
            (
                "grant-a",
                "grant-a",
            ),
        ),
        (
            "delete_exact",
            (
                "grant-a",
                "grant-a",
            ),
        ),
    ],
)
def test_fixture_collection_rejects_duplicate_operation_ids(
    method_name,
    values,
):
    from ai_core.rag_pipeline.ingestion.sedia_chroma_partial_upsert import (
        SediaChromaFixtureCollection,
    )

    collection = SediaChromaFixtureCollection()
    method = getattr(
        collection,
        method_name,
    )

    with pytest.raises(
        ValueError,
        match="unique",
    ):
        method(values)


def test_fixture_collection_rejects_duplicate_initial_ids():
    from ai_core.rag_pipeline.ingestion.sedia_chroma_partial_upsert import (
        SediaChromaFixtureCollection,
    )

    record = _stored_record(
        "grant-a",
        marker=0.1,
    )

    with pytest.raises(
        ValueError,
        match="unique",
    ):
        SediaChromaFixtureCollection(
            records=(
                record,
                record,
            )
        )


def test_fixture_collection_metadata_copy_is_isolated():
    record = _stored_record(
        "grant-a",
        marker=0.1,
    )

    metadata = record.metadata_dict
    metadata["status"] = "changed"

    assert (
        record.metadata_dict["status"]
        == "open"
    )
