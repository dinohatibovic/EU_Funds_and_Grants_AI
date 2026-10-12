"""Pure contracts for controlled SEDIA apply orchestration.

This module defines deterministic context, lifecycle and receipt
contracts. It deliberately contains no database, Chroma, snapshot or
network implementation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from ai_core.rag_pipeline.grant_metadata import (
    GrantMetadata,
)
from ai_core.rag_pipeline.ingestion.sync_planner import (
    validate_hash_snapshot,
)


class SediaControlledApplyError(RuntimeError):
    """Base error for controlled apply contract violations."""


class SediaApplyReceiptError(
    SediaControlledApplyError
):
    """Raised when a writer receipt violates the apply contract."""


SediaMutationAction = Literal[
    "insert",
    "update",
]


@dataclass(frozen=True)
class SediaApplyMutation:
    """One ordered INSERT or UPDATE mutation."""

    grant_id: str
    action: SediaMutationAction

    def __post_init__(self) -> None:
        if (
            not isinstance(self.grant_id, str)
            or not self.grant_id.strip()
            or self.grant_id != self.grant_id.strip()
        ):
            raise ValueError(
                "mutation grant_id must be a "
                "non-empty normalized string"
            )

        if self.action not in {
            "insert",
            "update",
        }:
            raise ValueError(
                "mutation action must be "
                "'insert' or 'update'"
            )


@dataclass(frozen=True)
class SediaApplyContext:
    """Deterministic identity and expectations for one apply run."""

    source_id: str
    run_id: str
    previous_snapshot_fingerprint: str
    target_snapshot_fingerprint: str
    expected_insert_count: int
    expected_update_count: int
    changed_grant_ids: tuple[str, ...]
    mutations: tuple[SediaApplyMutation, ...] = ()

    @property
    def expected_changed_count(self) -> int:
        """Return the number of expected writer mutations."""

        return (
            self.expected_insert_count
            + self.expected_update_count
        )


@dataclass(frozen=True)
class SediaPreparedApply:
    """Opaque prepared-writer handle bound to one run."""

    run_id: str
    transaction_id: str
    prepared_grant_ids: tuple[str, ...]


@dataclass(frozen=True)
class SediaApplyReceipt:
    """Immutable evidence returned by a successful commit."""

    run_id: str
    transaction_id: str
    committed_insert_count: int
    committed_update_count: int
    committed_grant_ids: tuple[str, ...]
    committed: bool = True

    @property
    def committed_changed_count(self) -> int:
        """Return the number of committed mutations."""

        return (
            self.committed_insert_count
            + self.committed_update_count
        )


RollbackStatus = Literal[
    "rolled_back",
    "rollback_failed",
    "rollback_unknown",
]


@dataclass(frozen=True)
class SediaRollbackResult:
    """Immutable evidence returned by one rollback attempt."""

    run_id: str
    transaction_id: str
    status: RollbackStatus
    detail: str = ""

    @property
    def rolled_back(self) -> bool:
        """Return whether rollback is confirmed successful."""

        return self.status == "rolled_back"

    @property
    def recovery_required(self) -> bool:
        """Return whether automatic recovery is incomplete."""

        return self.status != "rolled_back"


@runtime_checkable
class SediaControlledWriter(Protocol):
    """Lifecycle required from a controlled apply writer."""

    def prepare(
        self,
        grants: Sequence[GrantMetadata],
        context: SediaApplyContext,
    ) -> SediaPreparedApply:
        """Prepare a writer transaction without committing it."""

    def commit(
        self,
        prepared: SediaPreparedApply,
    ) -> SediaApplyReceipt:
        """Commit one previously prepared transaction."""

    def rollback(
        self,
        prepared: SediaPreparedApply,
        cause: BaseException,
    ) -> SediaRollbackResult:
        """Attempt rollback for one prepared transaction."""


def snapshot_fingerprint(
    hashes: Mapping[str, str],
) -> str:
    """Return a deterministic SHA-256 fingerprint of a snapshot."""

    validated = validate_hash_snapshot(
        hashes
    )

    serialized = json.dumps(
        dict(sorted(validated.items())),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    return hashlib.sha256(
        serialized
    ).hexdigest()


def build_apply_run_id(
    *,
    source_id: str,
    previous_snapshot_fingerprint: str,
    target_snapshot_fingerprint: str,
    expected_insert_count: int,
    expected_update_count: int,
    changed_grant_ids: Sequence[str],
    mutations: Sequence[
        SediaApplyMutation
    ] = (),
) -> str:
    """Return a deterministic content-derived apply run identifier."""

    if not isinstance(source_id, str):
        raise TypeError(
            "source_id must be a string"
        )

    normalized_source_id = source_id.strip()

    if (
        not normalized_source_id
        or normalized_source_id != source_id
    ):
        raise ValueError(
            "source_id must be non-empty and normalized"
        )

    if expected_insert_count < 0:
        raise ValueError(
            "expected_insert_count cannot be negative"
        )

    if expected_update_count < 0:
        raise ValueError(
            "expected_update_count cannot be negative"
        )

    normalized_ids = tuple(
        changed_grant_ids
    )

    if any(
        not isinstance(grant_id, str)
        or not grant_id.strip()
        or grant_id != grant_id.strip()
        for grant_id in normalized_ids
    ):
        raise ValueError(
            "changed grant IDs must be "
            "non-empty normalized strings"
        )

    if len(set(normalized_ids)) != len(
        normalized_ids
    ):
        raise ValueError(
            "changed grant IDs must be unique"
        )

    expected_changed_count = (
        expected_insert_count
        + expected_update_count
    )

    if len(normalized_ids) != expected_changed_count:
        raise ValueError(
            "changed grant ID count must match "
            "expected mutations"
        )

    normalized_mutations = tuple(
        mutations
    )

    if normalized_mutations:
        mutation_ids = tuple(
            mutation.grant_id
            for mutation in normalized_mutations
        )

        if mutation_ids != normalized_ids:
            raise ValueError(
                "mutation IDs must match changed "
                "grant IDs in the same order"
            )

        insert_count = sum(
            mutation.action == "insert"
            for mutation in normalized_mutations
        )
        update_count = sum(
            mutation.action == "update"
            for mutation in normalized_mutations
        )

        if insert_count != expected_insert_count:
            raise ValueError(
                "insert mutation count must match "
                "expected_insert_count"
            )

        if update_count != expected_update_count:
            raise ValueError(
                "update mutation count must match "
                "expected_update_count"
            )

    payload = {
        "source_id": normalized_source_id,
        "previous_snapshot_fingerprint": (
            previous_snapshot_fingerprint
        ),
        "target_snapshot_fingerprint": (
            target_snapshot_fingerprint
        ),
        "expected_insert_count": (
            expected_insert_count
        ),
        "expected_update_count": (
            expected_update_count
        ),
        "changed_grant_ids": list(
            normalized_ids
        ),
    }

    if normalized_mutations:
        payload["mutations"] = [
            {
                "grant_id": mutation.grant_id,
                "action": mutation.action,
            }
            for mutation in normalized_mutations
        ]

    serialized = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    digest = hashlib.sha256(
        serialized
    ).hexdigest()

    return (
        normalized_source_id
        + ":"
        + digest
    )


def build_apply_context(
    *,
    source_id: str,
    previous_hashes: Mapping[str, str],
    target_hashes: Mapping[str, str],
    expected_insert_count: int,
    expected_update_count: int,
    changed_grant_ids: Sequence[str],
    mutations: Sequence[
        SediaApplyMutation
    ] = (),
) -> SediaApplyContext:
    """Build one deterministic controlled-apply context."""

    previous_fingerprint = snapshot_fingerprint(
        previous_hashes
    )
    target_fingerprint = snapshot_fingerprint(
        target_hashes
    )
    normalized_ids = tuple(
        changed_grant_ids
    )
    normalized_mutations = tuple(
        mutations
    )

    run_id = build_apply_run_id(
        source_id=source_id,
        previous_snapshot_fingerprint=(
            previous_fingerprint
        ),
        target_snapshot_fingerprint=(
            target_fingerprint
        ),
        expected_insert_count=(
            expected_insert_count
        ),
        expected_update_count=(
            expected_update_count
        ),
        changed_grant_ids=normalized_ids,
        mutations=normalized_mutations,
    )

    return SediaApplyContext(
        source_id=source_id,
        run_id=run_id,
        previous_snapshot_fingerprint=(
            previous_fingerprint
        ),
        target_snapshot_fingerprint=(
            target_fingerprint
        ),
        expected_insert_count=(
            expected_insert_count
        ),
        expected_update_count=(
            expected_update_count
        ),
        changed_grant_ids=normalized_ids,
        mutations=normalized_mutations,
    )


def validate_prepared_apply(
    prepared: SediaPreparedApply,
    context: SediaApplyContext,
) -> None:
    """Validate that a prepared handle matches its context."""

    if not prepared.transaction_id.strip():
        raise SediaControlledApplyError(
            "prepared transaction_id must be non-empty"
        )

    if prepared.run_id != context.run_id:
        raise SediaControlledApplyError(
            "prepared run_id does not match context"
        )

    if (
        prepared.prepared_grant_ids
        != context.changed_grant_ids
    ):
        raise SediaControlledApplyError(
            "prepared grant IDs do not match context"
        )


def validate_apply_receipt(
    receipt: SediaApplyReceipt,
    context: SediaApplyContext,
    prepared: SediaPreparedApply,
) -> None:
    """Validate immutable writer evidence before snapshot commit."""

    if receipt.committed is not True:
        raise SediaApplyReceiptError(
            "writer receipt is not committed"
        )

    if receipt.run_id != context.run_id:
        raise SediaApplyReceiptError(
            "writer receipt run_id mismatch"
        )

    if (
        receipt.transaction_id
        != prepared.transaction_id
    ):
        raise SediaApplyReceiptError(
            "writer receipt transaction_id mismatch"
        )

    if (
        receipt.committed_insert_count
        != context.expected_insert_count
    ):
        raise SediaApplyReceiptError(
            "writer receipt insert count mismatch"
        )

    if (
        receipt.committed_update_count
        != context.expected_update_count
    ):
        raise SediaApplyReceiptError(
            "writer receipt update count mismatch"
        )

    if (
        receipt.committed_changed_count
        != context.expected_changed_count
    ):
        raise SediaApplyReceiptError(
            "writer receipt changed count mismatch"
        )

    if (
        receipt.committed_grant_ids
        != context.changed_grant_ids
    ):
        raise SediaApplyReceiptError(
            "writer receipt grant IDs mismatch"
        )


def validate_rollback_result(
    result: SediaRollbackResult,
    context: SediaApplyContext,
    prepared: SediaPreparedApply,
) -> None:
    """Validate rollback evidence for one prepared transaction."""

    if result.run_id != context.run_id:
        raise SediaControlledApplyError(
            "rollback result run_id mismatch"
        )

    if (
        result.transaction_id
        != prepared.transaction_id
    ):
        raise SediaControlledApplyError(
            "rollback result transaction_id mismatch"
        )

    if result.status not in {
        "rolled_back",
        "rollback_failed",
        "rollback_unknown",
    }:
        raise SediaControlledApplyError(
            "rollback result status is invalid"
        )

    if (
        result.status != "rolled_back"
        and not result.detail.strip()
    ):
        raise SediaControlledApplyError(
            "non-success rollback result "
            "requires detail"
        )
