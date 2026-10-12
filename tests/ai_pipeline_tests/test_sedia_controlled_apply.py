"""Tests for the pure SEDIA controlled-apply contract."""

from dataclasses import FrozenInstanceError
from hashlib import sha256

import pytest

from ai_core.rag_pipeline.ingestion.sedia_controlled_apply import (
    SediaApplyContext,
    SediaApplyMutation,
    SediaApplyReceipt,
    SediaApplyReceiptError,
    SediaControlledApplyError,
    SediaControlledWriter,
    SediaPreparedApply,
    SediaRollbackResult,
    build_apply_context,
    build_apply_run_id,
    snapshot_fingerprint,
    validate_apply_receipt,
    validate_prepared_apply,
    validate_rollback_result,
)

HASH_A = sha256(b"A").hexdigest()
HASH_B = sha256(b"B").hexdigest()
HASH_C = sha256(b"C").hexdigest()


def context() -> SediaApplyContext:
    """Return one deterministic synthetic apply context."""

    return build_apply_context(
        source_id="eu_sedia",
        previous_hashes={
            "A": HASH_A,
        },
        target_hashes={
            "A": HASH_B,
            "B": HASH_C,
        },
        expected_insert_count=1,
        expected_update_count=1,
        changed_grant_ids=(
            "A",
            "B",
        ),
    )


def prepared(
    apply_context: SediaApplyContext,
) -> SediaPreparedApply:
    """Return one valid synthetic prepared handle."""

    return SediaPreparedApply(
        run_id=apply_context.run_id,
        transaction_id="txn-001",
        prepared_grant_ids=(
            "A",
            "B",
        ),
    )


def receipt(
    apply_context: SediaApplyContext,
) -> SediaApplyReceipt:
    """Return one valid synthetic immutable receipt."""

    return SediaApplyReceipt(
        run_id=apply_context.run_id,
        transaction_id="txn-001",
        committed_insert_count=1,
        committed_update_count=1,
        committed_grant_ids=(
            "A",
            "B",
        ),
        committed=True,
    )


def test_snapshot_fingerprint_is_order_independent():
    first = snapshot_fingerprint(
        {
            "A": HASH_A,
            "B": HASH_B,
        }
    )
    second = snapshot_fingerprint(
        {
            "B": HASH_B,
            "A": HASH_A,
        }
    )

    assert first == second
    assert len(first) == 64


def test_snapshot_fingerprint_changes_with_hashes():
    first = snapshot_fingerprint(
        {
            "A": HASH_A,
        }
    )
    second = snapshot_fingerprint(
        {
            "A": HASH_B,
        }
    )

    assert first != second


def test_apply_context_is_deterministic():
    first = context()
    second = context()

    assert first == second
    assert first.run_id == second.run_id
    assert first.run_id.startswith(
        "eu_sedia:"
    )
    assert len(
        first.run_id.split(":", 1)[1]
    ) == 64
    assert first.expected_changed_count == 2


def test_run_id_changes_with_target_snapshot():
    first = context()

    changed_target = build_apply_context(
        source_id="eu_sedia",
        previous_hashes={
            "A": HASH_A,
        },
        target_hashes={
            "A": HASH_C,
            "B": HASH_C,
        },
        expected_insert_count=1,
        expected_update_count=1,
        changed_grant_ids=(
            "A",
            "B",
        ),
    )

    assert first.run_id != changed_target.run_id


def test_run_id_preserves_changed_grant_order():
    first = context()

    reversed_ids = build_apply_context(
        source_id="eu_sedia",
        previous_hashes={
            "A": HASH_A,
        },
        target_hashes={
            "A": HASH_B,
            "B": HASH_C,
        },
        expected_insert_count=1,
        expected_update_count=1,
        changed_grant_ids=(
            "B",
            "A",
        ),
    )

    assert first.run_id != reversed_ids.run_id
    assert reversed_ids.changed_grant_ids == (
        "B",
        "A",
    )


@pytest.mark.parametrize(
    (
        "insert_count",
        "update_count",
        "grant_ids",
        "message",
    ),
    [
        (
            -1,
            0,
            (),
            "insert_count",
        ),
        (
            0,
            -1,
            (),
            "update_count",
        ),
        (
            1,
            0,
            (),
            "count must match",
        ),
        (
            1,
            1,
            ("A", "A"),
            "must be unique",
        ),
        (
            1,
            0,
            (" A ",),
            "normalized strings",
        ),
    ],
)
def test_run_id_rejects_invalid_expectations(
    insert_count,
    update_count,
    grant_ids,
    message,
):
    with pytest.raises(
        ValueError,
        match=message,
    ):
        build_apply_run_id(
            source_id="eu_sedia",
            previous_snapshot_fingerprint="a" * 64,
            target_snapshot_fingerprint="b" * 64,
            expected_insert_count=insert_count,
            expected_update_count=update_count,
            changed_grant_ids=grant_ids,
        )


def test_run_id_rejects_invalid_source_id():
    for source_id in (
        "",
        " eu_sedia",
        "eu_sedia ",
    ):
        with pytest.raises(
            ValueError,
            match="source_id",
        ):
            build_apply_run_id(
                source_id=source_id,
                previous_snapshot_fingerprint=(
                    "a" * 64
                ),
                target_snapshot_fingerprint=(
                    "b" * 64
                ),
                expected_insert_count=0,
                expected_update_count=0,
                changed_grant_ids=(),
            )


def test_contract_models_are_immutable():
    apply_context = context()
    apply_prepared = prepared(
        apply_context
    )
    apply_receipt = receipt(
        apply_context
    )
    rollback = SediaRollbackResult(
        run_id=apply_context.run_id,
        transaction_id="txn-001",
        status="rolled_back",
    )

    for value, attribute in (
        (
            apply_context,
            "source_id",
        ),
        (
            apply_prepared,
            "transaction_id",
        ),
        (
            apply_receipt,
            "committed",
        ),
        (
            rollback,
            "status",
        ),
    ):
        with pytest.raises(
            FrozenInstanceError,
        ):
            setattr(
                value,
                attribute,
                "modified",
            )


def test_valid_prepared_handle_and_receipt_pass():
    apply_context = context()
    apply_prepared = prepared(
        apply_context
    )
    apply_receipt = receipt(
        apply_context
    )

    validate_prepared_apply(
        apply_prepared,
        apply_context,
    )
    validate_apply_receipt(
        apply_receipt,
        apply_context,
        apply_prepared,
    )

    assert (
        apply_receipt.committed_changed_count
        == 2
    )


@pytest.mark.parametrize(
    (
        "replacement",
        "message",
    ),
    [
        (
            {
                "run_id": "other-run",
                "transaction_id": "txn-001",
                "prepared_grant_ids": (
                    "A",
                    "B",
                ),
            },
            "run_id",
        ),
        (
            {
                "run_id": None,
                "transaction_id": "",
                "prepared_grant_ids": (
                    "A",
                    "B",
                ),
            },
            "transaction_id",
        ),
        (
            {
                "run_id": None,
                "transaction_id": "txn-001",
                "prepared_grant_ids": (
                    "B",
                    "A",
                ),
            },
            "grant IDs",
        ),
    ],
)
def test_invalid_prepared_handle_is_rejected(
    replacement,
    message,
):
    apply_context = context()

    run_id = replacement["run_id"]

    if run_id is None:
        run_id = apply_context.run_id

    candidate = SediaPreparedApply(
        run_id=run_id,
        transaction_id=(
            replacement["transaction_id"]
        ),
        prepared_grant_ids=(
            replacement[
                "prepared_grant_ids"
            ]
        ),
    )

    with pytest.raises(
        SediaControlledApplyError,
        match=message,
    ):
        validate_prepared_apply(
            candidate,
            apply_context,
        )


@pytest.mark.parametrize(
    (
        "changes",
        "message",
    ),
    [
        (
            {
                "committed": False,
            },
            "not committed",
        ),
        (
            {
                "run_id": "other-run",
            },
            "run_id",
        ),
        (
            {
                "transaction_id": "txn-other",
            },
            "transaction_id",
        ),
        (
            {
                "committed_insert_count": 2,
            },
            "insert count",
        ),
        (
            {
                "committed_update_count": 2,
            },
            "update count",
        ),
        (
            {
                "committed_grant_ids": (
                    "B",
                    "A",
                ),
            },
            "grant IDs",
        ),
    ],
)
def test_invalid_receipt_is_rejected(
    changes,
    message,
):
    apply_context = context()
    apply_prepared = prepared(
        apply_context
    )

    values = {
        "run_id": apply_context.run_id,
        "transaction_id": "txn-001",
        "committed_insert_count": 1,
        "committed_update_count": 1,
        "committed_grant_ids": (
            "A",
            "B",
        ),
        "committed": True,
    }
    values.update(changes)

    candidate = SediaApplyReceipt(
        **values
    )

    with pytest.raises(
        SediaApplyReceiptError,
        match=message,
    ):
        validate_apply_receipt(
            candidate,
            apply_context,
            apply_prepared,
        )


def test_runtime_protocol_accepts_complete_writer():
    class CompleteWriter:
        def prepare(self, grants, apply_context):
            return None

        def commit(self, apply_prepared):
            return None

        def rollback(
            self,
            apply_prepared,
            cause,
        ):
            return None

    class IncompleteWriter:
        def prepare(self, grants, apply_context):
            return None

    assert isinstance(
        CompleteWriter(),
        SediaControlledWriter,
    )
    assert not isinstance(
        IncompleteWriter(),
        SediaControlledWriter,
    )


@pytest.mark.parametrize(
    (
        "status",
        "detail",
        "rolled_back",
        "recovery_required",
    ),
    [
        (
            "rolled_back",
            "",
            True,
            False,
        ),
        (
            "rollback_failed",
            "writer rejected rollback",
            False,
            True,
        ),
        (
            "rollback_unknown",
            "writer outcome unavailable",
            False,
            True,
        ),
    ],
)
def test_rollback_outcome_properties(
    status,
    detail,
    rolled_back,
    recovery_required,
):
    apply_context = context()
    candidate = SediaRollbackResult(
        run_id=apply_context.run_id,
        transaction_id="txn-001",
        status=status,
        detail=detail,
    )

    assert candidate.rolled_back is rolled_back
    assert (
        candidate.recovery_required
        is recovery_required
    )


def test_valid_rollback_result_passes():
    apply_context = context()
    apply_prepared = prepared(
        apply_context
    )
    result = SediaRollbackResult(
        run_id=apply_context.run_id,
        transaction_id="txn-001",
        status="rolled_back",
    )

    validate_rollback_result(
        result,
        apply_context,
        apply_prepared,
    )


@pytest.mark.parametrize(
    (
        "run_id",
        "transaction_id",
        "status",
        "detail",
        "message",
    ),
    [
        (
            "other-run",
            "txn-001",
            "rolled_back",
            "",
            "run_id",
        ),
        (
            None,
            "txn-other",
            "rolled_back",
            "",
            "transaction_id",
        ),
        (
            None,
            "txn-001",
            "rollback_failed",
            "",
            "requires detail",
        ),
        (
            None,
            "txn-001",
            "rollback_unknown",
            "",
            "requires detail",
        ),
    ],
)
def test_invalid_rollback_result_is_rejected(
    run_id,
    transaction_id,
    status,
    detail,
    message,
):
    apply_context = context()
    apply_prepared = prepared(
        apply_context
    )

    candidate = SediaRollbackResult(
        run_id=(
            apply_context.run_id
            if run_id is None
            else run_id
        ),
        transaction_id=transaction_id,
        status=status,
        detail=detail,
    )

    with pytest.raises(
        SediaControlledApplyError,
        match=message,
    ):
        validate_rollback_result(
            candidate,
            apply_context,
            apply_prepared,
        )


def test_contract_module_has_no_external_write_imports():
    from pathlib import Path

    source = Path(
        "ai_core/rag_pipeline/ingestion/"
        "sedia_controlled_apply.py"
    ).read_text(encoding="utf-8")

    forbidden = (
        "psycopg",
        "sqlalchemy",
        "chromadb",
        "requests",
        "httpx",
        "HashSnapshotStore",
        "snapshot_store.save",
        "collection.upsert",
    )

    for marker in forbidden:
        assert marker not in source

def test_apply_mutation_is_immutable_and_validated():
    mutation = SediaApplyMutation(
        grant_id="grant-1",
        action="insert",
    )

    assert mutation.grant_id == "grant-1"
    assert mutation.action == "insert"

    with pytest.raises(
        AttributeError,
    ):
        mutation.action = "update"

    with pytest.raises(
        ValueError,
        match="grant_id",
    ):
        SediaApplyMutation(
            grant_id=" grant-1 ",
            action="insert",
        )

    with pytest.raises(
        ValueError,
        match="action",
    ):
        SediaApplyMutation(
            grant_id="grant-1",
            action="delete",
        )


def test_apply_run_id_changes_when_mutation_actions_change():
    common = {
        "source_id": "eu_sedia",
        "previous_snapshot_fingerprint": "a" * 64,
        "target_snapshot_fingerprint": "b" * 64,
        "expected_insert_count": 1,
        "expected_update_count": 1,
        "changed_grant_ids": (
            "grant-1",
            "grant-2",
        ),
    }

    first = build_apply_run_id(
        **common,
        mutations=(
            SediaApplyMutation(
                grant_id="grant-1",
                action="insert",
            ),
            SediaApplyMutation(
                grant_id="grant-2",
                action="update",
            ),
        ),
    )
    second = build_apply_run_id(
        **common,
        mutations=(
            SediaApplyMutation(
                grant_id="grant-1",
                action="update",
            ),
            SediaApplyMutation(
                grant_id="grant-2",
                action="insert",
            ),
        ),
    )

    assert first != second


def test_apply_context_preserves_ordered_mutations():
    mutations = (
        SediaApplyMutation(
            grant_id="grant-1",
            action="insert",
        ),
        SediaApplyMutation(
            grant_id="grant-2",
            action="update",
        ),
    )

    context = build_apply_context(
        source_id="eu_sedia",
        previous_hashes={
            "grant-2": "a" * 64,
        },
        target_hashes={
            "grant-1": "b" * 64,
            "grant-2": "c" * 64,
        },
        expected_insert_count=1,
        expected_update_count=1,
        changed_grant_ids=(
            "grant-1",
            "grant-2",
        ),
        mutations=mutations,
    )

    assert context.mutations == mutations
    assert tuple(
        mutation.grant_id
        for mutation in context.mutations
    ) == context.changed_grant_ids


@pytest.mark.parametrize(
    "mutations, message",
    [
        (
            (
                SediaApplyMutation(
                    grant_id="grant-2",
                    action="update",
                ),
                SediaApplyMutation(
                    grant_id="grant-1",
                    action="insert",
                ),
            ),
            "same order",
        ),
        (
            (
                SediaApplyMutation(
                    grant_id="grant-1",
                    action="update",
                ),
                SediaApplyMutation(
                    grant_id="grant-2",
                    action="update",
                ),
            ),
            "insert mutation count",
        ),
    ],
)
def test_apply_run_id_rejects_invalid_mutation_contract(
    mutations,
    message,
):
    with pytest.raises(
        ValueError,
        match=message,
    ):
        build_apply_run_id(
            source_id="eu_sedia",
            previous_snapshot_fingerprint="a" * 64,
            target_snapshot_fingerprint="b" * 64,
            expected_insert_count=1,
            expected_update_count=1,
            changed_grant_ids=(
                "grant-1",
                "grant-2",
            ),
            mutations=mutations,
        )
