"""Deterministic content hashing and planning for incremental grant sync."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum

from ai_core.rag_pipeline.grant_metadata import GrantMetadata


class SyncPlannerError(ValueError):
    """Raised when sync input violates the planner contract."""


class SyncAction(str, Enum):
    """Supported incremental synchronization actions."""

    INSERT = "insert"
    UPDATE = "update"
    SKIP = "skip"


@dataclass(frozen=True)
class PlannedGrant:
    """One deterministic synchronization decision."""

    grant_id: str
    action: SyncAction
    content_hash: str
    grant: GrantMetadata


@dataclass(frozen=True)
class SyncPlan:
    """Immutable collection of synchronization decisions."""

    items: tuple

    @property
    def inserts(self) -> tuple:
        """Return records that do not exist in the previous snapshot."""

        return tuple(
            item
            for item in self.items
            if item.action is SyncAction.INSERT
        )

    @property
    def updates(self) -> tuple:
        """Return records whose canonical content changed."""

        return tuple(
            item
            for item in self.items
            if item.action is SyncAction.UPDATE
        )

    @property
    def skips(self) -> tuple:
        """Return records whose canonical content is unchanged."""

        return tuple(
            item
            for item in self.items
            if item.action is SyncAction.SKIP
        )

    @property
    def counts(self) -> dict:
        """Return deterministic action counts."""

        return {
            SyncAction.INSERT.value: len(self.inserts),
            SyncAction.UPDATE.value: len(self.updates),
            SyncAction.SKIP.value: len(self.skips),
            "total": len(self.items),
        }


_ORDER_INSENSITIVE_LIST_FIELDS = (
    "regions",
    "beneficiary_types",
    "sectors",
)


def canonical_grant_payload(
    grant: GrantMetadata,
) -> dict:
    """Build the canonical payload used for change detection."""

    if not isinstance(grant, GrantMetadata):
        raise SyncPlannerError(
            "grant must be a GrantMetadata instance"
        )

    payload = grant.model_dump(
        mode="json",
        exclude_none=False,
    )

    for field_name in _ORDER_INSENSITIVE_LIST_FIELDS:
        values = payload.get(field_name)

        if not isinstance(values, list):
            raise SyncPlannerError(
                f"{field_name} must be a list"
            )

        payload[field_name] = sorted(
            values,
            key=lambda value: (
                value.casefold(),
                value,
            ),
        )

    return payload


def stable_grant_hash(
    grant: GrantMetadata,
) -> str:
    """Return a stable SHA-256 hash of canonical grant content."""

    canonical_json = json.dumps(
        canonical_grant_payload(grant),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )

    return hashlib.sha256(
        canonical_json.encode("utf-8")
    ).hexdigest()


def build_hash_snapshot(
    grants: Iterable,
) -> dict:
    """Build a grant_id to content_hash snapshot."""

    snapshot = {}

    for grant in grants:
        if not isinstance(grant, GrantMetadata):
            raise SyncPlannerError(
                "all grants must be GrantMetadata instances"
            )

        if grant.id in snapshot:
            raise SyncPlannerError(
                f"duplicate grant id: {grant.id}"
            )

        snapshot[grant.id] = stable_grant_hash(grant)

    return snapshot


def validate_hash_snapshot(
    snapshot: Mapping,
) -> dict:
    """Validate and copy an existing hash snapshot."""

    if not isinstance(snapshot, Mapping):
        raise SyncPlannerError(
            "previous_hashes must be a mapping"
        )

    validated = {}

    for grant_id, content_hash in snapshot.items():
        if not isinstance(grant_id, str):
            raise SyncPlannerError(
                "snapshot grant ids must be strings"
            )

        normalized_id = grant_id.strip()

        if not normalized_id:
            raise SyncPlannerError(
                "snapshot grant ids must not be empty"
            )

        if normalized_id != grant_id:
            raise SyncPlannerError(
                "snapshot grant ids must already be normalized"
            )

        if not isinstance(content_hash, str):
            raise SyncPlannerError(
                "snapshot hashes must be strings"
            )

        normalized_hash = content_hash.strip().lower()

        if len(normalized_hash) != 64:
            raise SyncPlannerError(
                f"invalid SHA-256 hash for grant: {grant_id}"
            )

        if any(
            character not in "0123456789abcdef"
            for character in normalized_hash
        ):
            raise SyncPlannerError(
                f"invalid SHA-256 hash for grant: {grant_id}"
            )

        validated[grant_id] = normalized_hash

    return validated


def plan_incremental_sync(
    grants: Iterable,
    previous_hashes: Mapping,
) -> SyncPlan:
    """Plan INSERT, UPDATE and SKIP actions in input order."""

    validated_previous = validate_hash_snapshot(
        previous_hashes
    )

    planned_items = []
    seen_ids = set()

    for grant in grants:
        if not isinstance(grant, GrantMetadata):
            raise SyncPlannerError(
                "all grants must be GrantMetadata instances"
            )

        if grant.id in seen_ids:
            raise SyncPlannerError(
                f"duplicate grant id: {grant.id}"
            )

        seen_ids.add(grant.id)

        current_hash = stable_grant_hash(grant)
        previous_hash = validated_previous.get(
            grant.id
        )

        if previous_hash is None:
            action = SyncAction.INSERT
        elif previous_hash == current_hash:
            action = SyncAction.SKIP
        else:
            action = SyncAction.UPDATE

        planned_items.append(
            PlannedGrant(
                grant_id=grant.id,
                action=action,
                content_hash=current_hash,
                grant=grant,
            )
        )

    return SyncPlan(
        items=tuple(planned_items)
    )
