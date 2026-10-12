"""Pure preparation contract for SEDIA Chroma partial upserts.

This module creates deterministic, immutable partial-upsert plans.
It deliberately performs no ChromaDB, embedding API, network,
snapshot, database or filesystem write operation.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ai_core.rag_pipeline.grant_metadata import (
    GrantMetadata,
)
from ai_core.rag_pipeline.ingestion.sedia_controlled_apply import (
    SediaApplyContext,
    SediaApplyMutation,
    SediaApplyReceipt,
    SediaPreparedApply,
    SediaRollbackResult,
)


class SediaChromaPartialUpsertError(
    ValueError
):
    """Raised when a partial-upsert plan is invalid."""


ChromaMetadataValue = str | int
FrozenChromaMetadata = tuple[
    tuple[str, ChromaMetadataValue],
    ...,
]
EmbeddingVector = tuple[float, ...]


@dataclass(frozen=True)
class SediaChromaPreparedRecord:
    """One immutable Chroma mutation prepared without writing."""

    grant_id: str
    action: str
    document: str
    metadata: FrozenChromaMetadata
    embedding: EmbeddingVector

    @property
    def metadata_dict(
        self,
    ) -> dict[str, ChromaMetadataValue]:
        """Return a fresh mutable copy for a future adapter."""

        return dict(self.metadata)


@dataclass(frozen=True)
class SediaChromaPartialUpsertPlan:
    """Immutable preparation result for one controlled apply run."""

    run_id: str
    transaction_id: str
    records: tuple[
        SediaChromaPreparedRecord,
        ...,
    ]
    embedding_dimension: int

    @property
    def grant_ids(self) -> tuple[str, ...]:
        """Return all prepared grant IDs in controlled order."""

        return tuple(
            record.grant_id
            for record in self.records
        )

    @property
    def insert_ids(self) -> tuple[str, ...]:
        """Return ordered INSERT IDs."""

        return tuple(
            record.grant_id
            for record in self.records
            if record.action == "insert"
        )

    @property
    def update_ids(self) -> tuple[str, ...]:
        """Return ordered UPDATE IDs."""

        return tuple(
            record.grant_id
            for record in self.records
            if record.action == "update"
        )


def _normalize_embedding(
    values: Sequence[float],
    *,
    grant_id: str,
) -> EmbeddingVector:
    """Validate and freeze one embedding vector."""

    if isinstance(
        values,
        (str, bytes),
    ):
        raise SediaChromaPartialUpsertError(
            f"embedding for {grant_id} "
            "must be a numeric sequence"
        )

    normalized: list[float] = []

    for value in values:
        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                (int, float),
            )
        ):
            raise SediaChromaPartialUpsertError(
                f"embedding for {grant_id} "
                "contains a non-numeric value"
            )

        number = float(value)

        if not math.isfinite(number):
            raise SediaChromaPartialUpsertError(
                f"embedding for {grant_id} "
                "contains a non-finite value"
            )

        normalized.append(number)

    if not normalized:
        raise SediaChromaPartialUpsertError(
            f"embedding for {grant_id} "
            "cannot be empty"
        )

    return tuple(normalized)


def _freeze_metadata(
    metadata: dict[str, ChromaMetadataValue],
    *,
    grant_id: str,
) -> FrozenChromaMetadata:
    """Validate and deterministically freeze Chroma metadata."""

    if metadata.get("grant_id") != grant_id:
        raise SediaChromaPartialUpsertError(
            "Chroma metadata grant_id mismatch"
        )

    for key, value in metadata.items():
        if not isinstance(key, str) or not key:
            raise SediaChromaPartialUpsertError(
                "Chroma metadata keys must be "
                "non-empty strings"
            )

        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                (str, int),
            )
        ):
            raise SediaChromaPartialUpsertError(
                "Chroma metadata values must be "
                "strings or integers"
            )

    return tuple(
        sorted(metadata.items())
    )


def _validate_alignment(
    grants: tuple[GrantMetadata, ...],
    context: SediaApplyContext,
    embeddings: tuple[
        Sequence[float],
        ...,
    ],
) -> None:
    """Validate controlled ordering and action-aware alignment."""

    if not context.mutations:
        raise SediaChromaPartialUpsertError(
            "action-aware mutations are required"
        )

    grant_ids = tuple(
        grant.id
        for grant in grants
    )

    mutation_ids = tuple(
        mutation.grant_id
        for mutation in context.mutations
    )

    if grant_ids != context.changed_grant_ids:
        raise SediaChromaPartialUpsertError(
            "grant IDs must match controlled "
            "changed_grant_ids in the same order"
        )

    if mutation_ids != grant_ids:
        raise SediaChromaPartialUpsertError(
            "mutation IDs must match grant IDs "
            "in the same order"
        )

    if len(embeddings) != len(grants):
        raise SediaChromaPartialUpsertError(
            "embedding count must match grant count"
        )

    if len(set(grant_ids)) != len(grant_ids):
        raise SediaChromaPartialUpsertError(
            "grant IDs must be unique"
        )

    insert_count = sum(
        mutation.action == "insert"
        for mutation in context.mutations
    )
    update_count = sum(
        mutation.action == "update"
        for mutation in context.mutations
    )

    if insert_count != context.expected_insert_count:
        raise SediaChromaPartialUpsertError(
            "planned INSERT count mismatch"
        )

    if update_count != context.expected_update_count:
        raise SediaChromaPartialUpsertError(
            "planned UPDATE count mismatch"
        )


def _build_record(
    grant: GrantMetadata,
    mutation: SediaApplyMutation,
    embedding: Sequence[float],
) -> SediaChromaPreparedRecord:
    """Build one immutable prepared record."""

    document = grant.to_embedding_text()

    if not document.strip():
        raise SediaChromaPartialUpsertError(
            f"embedding document for {grant.id} "
            "cannot be empty"
        )

    metadata = _freeze_metadata(
        grant.to_chroma_metadata(),
        grant_id=grant.id,
    )

    vector = _normalize_embedding(
        embedding,
        grant_id=grant.id,
    )

    return SediaChromaPreparedRecord(
        grant_id=grant.id,
        action=mutation.action,
        document=document,
        metadata=metadata,
        embedding=vector,
    )


def _build_transaction_id(
    *,
    context: SediaApplyContext,
    records: tuple[
        SediaChromaPreparedRecord,
        ...,
    ],
) -> str:
    """Build a deterministic transaction identity."""

    payload = {
        "run_id": context.run_id,
        "records": [
            {
                "grant_id": record.grant_id,
                "action": record.action,
                "document": record.document,
                "metadata": list(record.metadata),
                "embedding": list(record.embedding),
            }
            for record in records
        ],
    }

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

    return "chroma-partial:" + digest


def build_chroma_partial_upsert_plan(
    *,
    grants: Sequence[GrantMetadata],
    context: SediaApplyContext,
    embeddings: Sequence[
        Sequence[float]
    ],
) -> SediaChromaPartialUpsertPlan:
    """Build an immutable plan without executing external operations."""

    normalized_grants = tuple(grants)
    normalized_embeddings = tuple(
        embeddings
    )

    _validate_alignment(
        normalized_grants,
        context,
        normalized_embeddings,
    )

    records = tuple(
        _build_record(
            grant,
            mutation,
            embedding,
        )
        for grant, mutation, embedding in zip(
            normalized_grants,
            context.mutations,
            normalized_embeddings,
            strict=True,
        )
    )

    dimensions = {
        len(record.embedding)
        for record in records
    }

    if len(dimensions) != 1:
        raise SediaChromaPartialUpsertError(
            "all embeddings must have the "
            "same dimension"
        )

    embedding_dimension = next(
        iter(dimensions)
    )

    transaction_id = _build_transaction_id(
        context=context,
        records=records,
    )

    return SediaChromaPartialUpsertPlan(
        run_id=context.run_id,
        transaction_id=transaction_id,
        records=records,
        embedding_dimension=(
            embedding_dimension
        ),
    )

@dataclass(frozen=True)
class SediaChromaStoredRecord:
    """One immutable record stored by the fixture adapter."""

    grant_id: str
    document: str
    metadata: FrozenChromaMetadata
    embedding: EmbeddingVector

    @classmethod
    def from_prepared(
        cls,
        record: SediaChromaPreparedRecord,
    ) -> SediaChromaStoredRecord:
        """Build one stored record from a prepared mutation."""

        return cls(
            grant_id=record.grant_id,
            document=record.document,
            metadata=record.metadata,
            embedding=record.embedding,
        )

    @property
    def metadata_dict(
        self,
    ) -> dict[str, ChromaMetadataValue]:
        """Return a fresh mutable metadata copy."""

        return dict(self.metadata)


class SediaChromaFixtureCollectionError(
    RuntimeError
):
    """Raised by the fixture-only collection adapter."""


class SediaChromaFixtureCollection:
    """In-memory collection used only for lifecycle tests.

    The adapter deliberately has no ChromaDB dependency. It records
    exact calls and supports deterministic failure injection.
    """

    def __init__(
        self,
        records: Sequence[
            SediaChromaStoredRecord
        ] = (),
        *,
        fail_upsert_after: int | None = None,
        fail_delete_after: int | None = None,
    ) -> None:
        if (
            fail_upsert_after is not None
            and fail_upsert_after < 0
        ):
            raise ValueError(
                "fail_upsert_after cannot be negative"
            )

        if (
            fail_delete_after is not None
            and fail_delete_after < 0
        ):
            raise ValueError(
                "fail_delete_after cannot be negative"
            )

        normalized = tuple(records)
        ids = tuple(
            record.grant_id
            for record in normalized
        )

        if len(set(ids)) != len(ids):
            raise ValueError(
                "initial fixture record IDs "
                "must be unique"
            )

        self._records = {
            record.grant_id: record
            for record in normalized
        }
        self.fail_upsert_after = (
            fail_upsert_after
        )
        self.fail_delete_after = (
            fail_delete_after
        )

        self.get_calls: list[
            tuple[str, ...]
        ] = []
        self.upsert_calls: list[
            tuple[str, ...]
        ] = []
        self.delete_calls: list[
            tuple[str, ...]
        ] = []

    def snapshot(
        self,
    ) -> tuple[
        SediaChromaStoredRecord,
        ...,
    ]:
        """Return all records in deterministic ID order."""

        return tuple(
            self._records[grant_id]
            for grant_id in sorted(
                self._records
            )
        )

    def get_by_ids(
        self,
        grant_ids: Sequence[str],
    ) -> tuple[
        SediaChromaStoredRecord,
        ...,
    ]:
        """Return existing requested records in input order."""

        normalized = tuple(grant_ids)
        self._validate_ids(normalized)

        self.get_calls.append(
            normalized
        )

        return tuple(
            self._records[grant_id]
            for grant_id in normalized
            if grant_id in self._records
        )

    def upsert_exact(
        self,
        records: Sequence[
            SediaChromaStoredRecord
        ],
    ) -> tuple[str, ...]:
        """Upsert only supplied records, with optional failure."""

        normalized = tuple(records)
        ids = tuple(
            record.grant_id
            for record in normalized
        )
        self._validate_ids(ids)

        self.upsert_calls.append(ids)

        applied: list[str] = []

        for record in normalized:
            if (
                self.fail_upsert_after
                is not None
                and len(applied)
                >= self.fail_upsert_after
            ):
                raise SediaChromaFixtureCollectionError(
                    "fixture upsert failed after "
                    f"{len(applied)} records"
                )

            self._records[
                record.grant_id
            ] = record
            applied.append(
                record.grant_id
            )

        return tuple(applied)

    def delete_exact(
        self,
        grant_ids: Sequence[str],
    ) -> tuple[str, ...]:
        """Delete only supplied existing IDs, with optional failure."""

        normalized = tuple(grant_ids)
        self._validate_ids(normalized)

        self.delete_calls.append(
            normalized
        )

        deleted: list[str] = []

        for grant_id in normalized:
            if (
                self.fail_delete_after
                is not None
                and len(deleted)
                >= self.fail_delete_after
            ):
                raise SediaChromaFixtureCollectionError(
                    "fixture delete failed after "
                    f"{len(deleted)} records"
                )

            if grant_id in self._records:
                del self._records[
                    grant_id
                ]
                deleted.append(
                    grant_id
                )

        return tuple(deleted)

    def _validate_ids(
        self,
        grant_ids: tuple[str, ...],
    ) -> None:
        """Validate an ordered exact-ID operation."""

        if any(
            not isinstance(grant_id, str)
            or not grant_id.strip()
            or grant_id != grant_id.strip()
            for grant_id in grant_ids
        ):
            raise ValueError(
                "fixture grant IDs must be "
                "non-empty normalized strings"
            )

        if len(set(grant_ids)) != len(
            grant_ids
        ):
            raise ValueError(
                "fixture grant IDs must be unique"
            )

FixtureEmbeddingProvider = Callable[
    [tuple[str, ...]],
    Sequence[Sequence[float]],
]


@dataclass(frozen=True)
class SediaChromaFixturePreparedState:
    """Internal immutable state required for commit and rollback."""

    context: SediaApplyContext
    plan: SediaChromaPartialUpsertPlan
    previous_updates: tuple[
        SediaChromaStoredRecord,
        ...,
    ]
    original_changed_records: tuple[
        SediaChromaStoredRecord,
        ...,
    ]


class SediaChromaFixtureControlledWriter:
    """Fixture-only implementation of the controlled writer protocol."""

    def __init__(
        self,
        *,
        collection: SediaChromaFixtureCollection,
        embedding_provider: FixtureEmbeddingProvider,
    ) -> None:
        self.collection = collection
        self.embedding_provider = embedding_provider
        self._prepared: dict[
            str,
            SediaChromaFixturePreparedState,
        ] = {}

    def prepare(
        self,
        grants: Sequence[GrantMetadata],
        context: SediaApplyContext,
    ) -> SediaPreparedApply:
        """Prepare an in-memory transaction without collection writes."""

        normalized_grants = tuple(grants)

        if not context.mutations:
            raise SediaChromaPartialUpsertError(
                "action-aware mutations are required"
            )

        if tuple(
            grant.id
            for grant in normalized_grants
        ) != context.changed_grant_ids:
            raise SediaChromaPartialUpsertError(
                "prepared grants must match "
                "changed_grant_ids in order"
            )

        insert_ids = tuple(
            mutation.grant_id
            for mutation in context.mutations
            if mutation.action == "insert"
        )
        update_ids = tuple(
            mutation.grant_id
            for mutation in context.mutations
            if mutation.action == "update"
        )

        original_changed = (
            self.collection.get_by_ids(
                context.changed_grant_ids
            )
        )

        original_by_id = {
            record.grant_id: record
            for record in original_changed
        }

        unexpected_insert_ids = tuple(
            grant_id
            for grant_id in insert_ids
            if grant_id in original_by_id
        )

        if unexpected_insert_ids:
            raise SediaChromaPartialUpsertError(
                "INSERT IDs already exist in "
                "the fixture collection"
            )

        missing_update_ids = tuple(
            grant_id
            for grant_id in update_ids
            if grant_id not in original_by_id
        )

        if missing_update_ids:
            raise SediaChromaPartialUpsertError(
                "UPDATE IDs are missing from "
                "the fixture collection"
            )

        documents = tuple(
            grant.to_embedding_text()
            for grant in normalized_grants
        )

        embeddings = tuple(
            self.embedding_provider(
                documents
            )
        )

        plan = build_chroma_partial_upsert_plan(
            grants=normalized_grants,
            context=context,
            embeddings=embeddings,
        )

        if plan.transaction_id in self._prepared:
            raise SediaChromaPartialUpsertError(
                "transaction is already prepared"
            )

        previous_updates = tuple(
            original_by_id[grant_id]
            for grant_id in update_ids
        )

        state = SediaChromaFixturePreparedState(
            context=context,
            plan=plan,
            previous_updates=previous_updates,
            original_changed_records=(
                original_changed
            ),
        )

        self._prepared[
            plan.transaction_id
        ] = state

        return SediaPreparedApply(
            run_id=context.run_id,
            transaction_id=plan.transaction_id,
            prepared_grant_ids=(
                plan.grant_ids
            ),
        )

    def commit(
        self,
        prepared: SediaPreparedApply,
    ) -> SediaApplyReceipt:
        """Apply exactly the prepared changed records and verify them."""

        state = self._state_for(
            prepared
        )

        stored_records = tuple(
            SediaChromaStoredRecord.from_prepared(
                record
            )
            for record in state.plan.records
        )

        applied_ids = (
            self.collection.upsert_exact(
                stored_records
            )
        )

        if applied_ids != state.plan.grant_ids:
            raise SediaChromaFixtureCollectionError(
                "fixture commit applied ID mismatch"
            )

        readback = self.collection.get_by_ids(
            state.plan.grant_ids
        )

        if readback != stored_records:
            raise SediaChromaFixtureCollectionError(
                "fixture commit verification failed"
            )

        return SediaApplyReceipt(
            run_id=state.context.run_id,
            transaction_id=(
                state.plan.transaction_id
            ),
            committed_insert_count=(
                state.context.expected_insert_count
            ),
            committed_update_count=(
                state.context.expected_update_count
            ),
            committed_grant_ids=(
                state.plan.grant_ids
            ),
            committed=True,
        )

    def rollback(
        self,
        prepared: SediaPreparedApply,
        cause: BaseException,
    ) -> SediaRollbackResult:
        """Restore UPDATE records and remove only INSERT records."""

        del cause

        try:
            state = self._state_for(
                prepared
            )
        except SediaChromaPartialUpsertError:
            return SediaRollbackResult(
                run_id=prepared.run_id,
                transaction_id=(
                    prepared.transaction_id
                ),
                status="rollback_unknown",
                detail=(
                    "prepared fixture state "
                    "is unavailable"
                ),
            )

        try:
            if state.previous_updates:
                self.collection.upsert_exact(
                    state.previous_updates
                )

            if state.plan.insert_ids:
                self.collection.delete_exact(
                    state.plan.insert_ids
                )

            restored = (
                self.collection.get_by_ids(
                    state.context.changed_grant_ids
                )
            )

            if (
                restored
                != state.original_changed_records
            ):
                return SediaRollbackResult(
                    run_id=state.context.run_id,
                    transaction_id=(
                        state.plan.transaction_id
                    ),
                    status="rollback_failed",
                    detail=(
                        "fixture rollback state "
                        "verification failed"
                    ),
                )

        except (
            SediaChromaFixtureCollectionError,
            ValueError,
        ) as error:
            return SediaRollbackResult(
                run_id=state.context.run_id,
                transaction_id=(
                    state.plan.transaction_id
                ),
                status="rollback_failed",
                detail=(
                    "fixture rollback operation "
                    f"failed: {type(error).__name__}"
                ),
            )

        self._prepared.pop(
            state.plan.transaction_id,
            None,
        )

        return SediaRollbackResult(
            run_id=state.context.run_id,
            transaction_id=(
                state.plan.transaction_id
            ),
            status="rolled_back",
        )

    def _state_for(
        self,
        prepared: SediaPreparedApply,
    ) -> SediaChromaFixturePreparedState:
        """Return and validate one in-memory prepared state."""

        state = self._prepared.get(
            prepared.transaction_id
        )

        if state is None:
            raise SediaChromaPartialUpsertError(
                "prepared fixture state "
                "is unavailable"
            )

        if prepared.run_id != state.context.run_id:
            raise SediaChromaPartialUpsertError(
                "prepared run_id mismatch"
            )

        if (
            prepared.prepared_grant_ids
            != state.plan.grant_ids
        ):
            raise SediaChromaPartialUpsertError(
                "prepared grant IDs mismatch"
            )

        return state
