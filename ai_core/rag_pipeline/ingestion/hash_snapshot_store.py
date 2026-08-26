"""Atomic JSON persistence for incremental grant hash snapshots."""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path

from ai_core.rag_pipeline.ingestion.sync_planner import (
    SyncPlannerError,
    validate_hash_snapshot,
)


class HashSnapshotStoreError(RuntimeError):
    """Raised when a hash snapshot cannot be loaded or saved safely."""


_SOURCE_ID_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9_-]*$"
)


class HashSnapshotStore:
    """Persist validated SHA-256 snapshots as atomic JSON files."""

    SCHEMA_VERSION = 1
    HASH_ALGORITHM = "sha256"

    def __init__(
        self,
        directory: Path | str,
    ) -> None:
        self.directory = Path(directory)

    def snapshot_path(
        self,
        source_id: str,
    ) -> Path:
        """Return a safe snapshot path for one source."""

        if not isinstance(source_id, str):
            raise HashSnapshotStoreError(
                "source_id must be a string"
            )

        normalized = source_id.strip()

        if normalized != source_id:
            raise HashSnapshotStoreError(
                "source_id must already be normalized"
            )

        if not _SOURCE_ID_PATTERN.fullmatch(
            normalized
        ):
            raise HashSnapshotStoreError(
                "source_id contains unsupported characters"
            )

        return self.directory / (
            source_id + ".json"
        )

    def load(
        self,
        source_id: str,
    ) -> dict:
        """Load a validated snapshot or return an empty mapping."""

        path = self.snapshot_path(source_id)

        if not path.exists():
            return {}

        try:
            payload = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except OSError as exc:
            raise HashSnapshotStoreError(
                f"cannot read hash snapshot: {path}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise HashSnapshotStoreError(
                f"hash snapshot is not valid JSON: {path}"
            ) from exc

        if not isinstance(payload, dict):
            raise HashSnapshotStoreError(
                "hash snapshot root must be an object"
            )

        if payload.get("schema_version") != (
            self.SCHEMA_VERSION
        ):
            raise HashSnapshotStoreError(
                "unsupported hash snapshot schema"
            )

        if payload.get("source_id") != source_id:
            raise HashSnapshotStoreError(
                "hash snapshot source_id mismatch"
            )

        if payload.get("hash_algorithm") != (
            self.HASH_ALGORITHM
        ):
            raise HashSnapshotStoreError(
                "unsupported hash algorithm"
            )

        hashes = payload.get("hashes")

        try:
            validated = validate_hash_snapshot(
                hashes
            )
        except SyncPlannerError as exc:
            raise HashSnapshotStoreError(
                "hash snapshot contains invalid hashes"
            ) from exc

        if payload.get("record_count") != len(
            validated
        ):
            raise HashSnapshotStoreError(
                "hash snapshot record_count mismatch"
            )

        return validated

    def save(
        self,
        source_id: str,
        hashes: Mapping,
    ) -> Path:
        """Atomically write one validated hash snapshot."""

        path = self.snapshot_path(source_id)

        try:
            validated = validate_hash_snapshot(
                hashes
            )
        except SyncPlannerError as exc:
            raise HashSnapshotStoreError(
                "cannot save invalid hash snapshot"
            ) from exc

        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "source_id": source_id,
            "hash_algorithm": self.HASH_ALGORITHM,
            "record_count": len(validated),
            "hashes": dict(
                sorted(validated.items())
            ),
        }

        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        ) + "\n"

        temporary_path = None

        try:
            self.directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            file_descriptor, temporary_name = (
                tempfile.mkstemp(
                    prefix="." + source_id + ".",
                    suffix=".tmp",
                    dir=self.directory,
                    text=True,
                )
            )

            temporary_path = Path(
                temporary_name
            )

            with os.fdopen(
                file_descriptor,
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                handle.write(serialized)
                handle.flush()
                os.fsync(handle.fileno())

            os.replace(
                temporary_path,
                path,
            )

        except OSError as exc:
            if temporary_path is not None:
                temporary_path.unlink(
                    missing_ok=True
                )

            raise HashSnapshotStoreError(
                f"cannot write hash snapshot: {path}"
            ) from exc

        return path
