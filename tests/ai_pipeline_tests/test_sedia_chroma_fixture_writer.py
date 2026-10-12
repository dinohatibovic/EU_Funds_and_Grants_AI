"""Tests for the fixture-only controlled Chroma writer."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ai_core.rag_pipeline.grant_metadata import GrantMetadata
from ai_core.rag_pipeline.ingestion.sedia_chroma_partial_upsert import (
    SediaChromaFixtureCollection,
    SediaChromaFixtureControlledWriter,
    SediaChromaPartialUpsertError,
    SediaChromaStoredRecord,
)
from ai_core.rag_pipeline.ingestion.sedia_controlled_apply import (
    SediaApplyMutation,
    build_apply_context,
    validate_apply_receipt,
    validate_prepared_apply,
    validate_rollback_result,
)


def grant(grant_id: str, title: str) -> GrantMetadata:
    return GrantMetadata(
        id=grant_id,
        title=title,
        description=f"Description for {title}",
        category="Digital",
        status="open",
        verified_score=90,
        source_priority=95,
        regions=["BiH"],
        beneficiary_types=["SME"],
    )


def stored(
    grant_id: str,
    document: str,
) -> SediaChromaStoredRecord:
    return SediaChromaStoredRecord(
        grant_id=grant_id,
        document=document,
        metadata=(
            ("grant_id", grant_id),
            ("status", "open"),
        ),
        embedding=(
            0.1,
            0.2,
            0.3,
        ),
    )


def provider(documents):
    return tuple(
        (
            float(index + 1),
            float(index + 2),
            float(index + 3),
        )
        for index, _ in enumerate(documents)
    )


def fixture():
    new = grant("grant-new", "New Grant")
    updated = grant(
        "grant-existing",
        "Updated Grant",
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

    old = stored(
        "grant-existing",
        "Old Grant",
    )
    unrelated = stored(
        "grant-unrelated",
        "Unrelated Grant",
    )

    collection = SediaChromaFixtureCollection(
        records=(
            old,
            unrelated,
        )
    )

    writer = SediaChromaFixtureControlledWriter(
        collection=collection,
        embedding_provider=provider,
    )

    return (
        (new, updated),
        context,
        old,
        unrelated,
        collection,
        writer,
    )


def test_prepare_is_write_free_and_contract_valid():
    grants, context, old, unrelated, collection, writer = fixture()

    before = collection.snapshot()

    prepared = writer.prepare(
        grants,
        context,
    )

    validate_prepared_apply(
        prepared,
        context,
    )

    assert collection.snapshot() == before
    assert collection.upsert_calls == []
    assert collection.delete_calls == []
    assert prepared.prepared_grant_ids == (
        "grant-new",
        "grant-existing",
    )
    assert old in before
    assert unrelated in before


def test_commit_upserts_only_changed_records():
    grants, context, _, unrelated, collection, writer = fixture()

    prepared = writer.prepare(
        grants,
        context,
    )
    receipt = writer.commit(
        prepared
    )

    validate_apply_receipt(
        receipt,
        context,
        prepared,
    )

    snapshot = {
        record.grant_id: record
        for record in collection.snapshot()
    }

    assert set(snapshot) == {
        "grant-new",
        "grant-existing",
        "grant-unrelated",
    }
    assert snapshot[
        "grant-unrelated"
    ] == unrelated
    assert collection.delete_calls == []


def test_rollback_after_commit_restores_exact_state():
    grants, context, old, unrelated, collection, writer = fixture()

    before = collection.snapshot()

    prepared = writer.prepare(
        grants,
        context,
    )
    writer.commit(
        prepared
    )

    result = writer.rollback(
        prepared,
        RuntimeError("snapshot failed"),
    )

    validate_rollback_result(
        result,
        context,
        prepared,
    )

    assert result.status == "rolled_back"
    assert collection.snapshot() == before
    assert old in collection.snapshot()
    assert unrelated in collection.snapshot()


def test_partial_commit_failure_can_be_rolled_back():
    grants, context, old, unrelated, collection, writer = fixture()

    collection.fail_upsert_after = 1
    before = collection.snapshot()

    prepared = writer.prepare(
        grants,
        context,
    )

    with pytest.raises(
        Exception,
        match="fixture upsert failed",
    ):
        writer.commit(
            prepared
        )

    collection.fail_upsert_after = None

    result = writer.rollback(
        prepared,
        RuntimeError("partial commit"),
    )

    assert result.status == "rolled_back"
    assert collection.snapshot() == before
    assert old in collection.snapshot()
    assert unrelated in collection.snapshot()


def test_prepare_rejects_existing_insert_id():
    grants, context, _, _, collection, writer = fixture()

    collection.upsert_exact(
        (
            stored(
                "grant-new",
                "Already Exists",
            ),
        )
    )

    with pytest.raises(
        SediaChromaPartialUpsertError,
        match="INSERT IDs already exist",
    ):
        writer.prepare(
            grants,
            context,
        )


def test_prepare_rejects_missing_update_id():
    grants, context, _, _, _, _ = fixture()

    collection = SediaChromaFixtureCollection()
    writer = SediaChromaFixtureControlledWriter(
        collection=collection,
        embedding_provider=provider,
    )

    with pytest.raises(
        SediaChromaPartialUpsertError,
        match="UPDATE IDs are missing",
    ):
        writer.prepare(
            grants,
            context,
        )


def test_unknown_prepared_state_returns_rollback_unknown():
    grants, context, _, _, _, writer = fixture()

    prepared = writer.prepare(
        grants,
        context,
    )

    unknown = replace(
        prepared,
        transaction_id="missing-transaction",
    )

    result = writer.rollback(
        unknown,
        RuntimeError("unknown"),
    )

    assert result.status == "rollback_unknown"
    assert result.recovery_required is True
    assert result.detail


def test_tampered_prepared_handle_is_rejected():
    grants, context, _, _, _, writer = fixture()

    prepared = writer.prepare(
        grants,
        context,
    )

    tampered = replace(
        prepared,
        run_id="wrong-run",
    )

    with pytest.raises(
        SediaChromaPartialUpsertError,
        match="run_id mismatch",
    ):
        writer.commit(
            tampered
        )
