"""Tests for atomic JSON hash snapshot persistence."""

from __future__ import annotations

import json

import pytest

from ai_core.rag_pipeline.ingestion.hash_snapshot_store import (
    HashSnapshotStore,
    HashSnapshotStoreError,
)


HASH_A = "a" * 64
HASH_B = "b" * 64


def test_missing_snapshot_returns_empty_mapping(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)

    assert store.load("eu_sedia") == {}


def test_snapshot_path_uses_source_id(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)

    assert store.snapshot_path(
        "eu_sedia"
    ) == (
        tmp_path / "eu_sedia.json"
    )


def test_save_and_load_round_trip(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)

    path = store.save(
        "eu_sedia",
        {
            "grant-b": HASH_B,
            "grant-a": HASH_A,
        },
    )

    assert path == (
        tmp_path / "eu_sedia.json"
    )

    assert store.load("eu_sedia") == {
        "grant-a": HASH_A,
        "grant-b": HASH_B,
    }


def test_saved_json_has_stable_contract(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)

    path = store.save(
        "eu_sedia",
        {
            "grant-a": HASH_A,
        },
    )

    payload = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert payload == {
        "hash_algorithm": "sha256",
        "hashes": {
            "grant-a": HASH_A,
        },
        "record_count": 1,
        "schema_version": 1,
        "source_id": "eu_sedia",
    }


def test_saved_json_ends_with_newline(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)

    path = store.save(
        "eu_sedia",
        {
            "grant-a": HASH_A,
        },
    )

    assert path.read_bytes().endswith(
        b"\n"
    )


def test_save_sorts_hash_keys(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)

    path = store.save(
        "eu_sedia",
        {
            "grant-z": HASH_B,
            "grant-a": HASH_A,
        },
    )

    text = path.read_text(
        encoding="utf-8"
    )

    assert text.index(
        '"grant-a"'
    ) < text.index(
        '"grant-z"'
    )


def test_save_replaces_existing_snapshot(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)

    store.save(
        "eu_sedia",
        {
            "grant-a": HASH_A,
        },
    )

    store.save(
        "eu_sedia",
        {
            "grant-b": HASH_B,
        },
    )

    assert store.load("eu_sedia") == {
        "grant-b": HASH_B,
    }


def test_empty_snapshot_round_trip(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)

    store.save(
        "eu_sedia",
        {},
    )

    assert store.load("eu_sedia") == {}


def test_invalid_hash_is_rejected(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)

    with pytest.raises(
        HashSnapshotStoreError,
        match="invalid hash snapshot",
    ):
        store.save(
            "eu_sedia",
            {
                "grant-a": "invalid",
            },
        )


@pytest.mark.parametrize(
    "source_id",
    [
        "",
        " eu_sedia",
        "eu_sedia ",
        "EU SEDIA",
        "../escape",
        "eu/sedia",
        "eu.sedia",
    ],
)
def test_unsafe_source_ids_are_rejected(
    tmp_path,
    source_id,
):
    store = HashSnapshotStore(tmp_path)

    with pytest.raises(
        HashSnapshotStoreError
    ):
        store.snapshot_path(
            source_id
        )


def test_invalid_json_is_rejected(
    tmp_path,
):
    path = tmp_path / "eu_sedia.json"

    path.write_text(
        "{invalid",
        encoding="utf-8",
    )

    store = HashSnapshotStore(tmp_path)

    with pytest.raises(
        HashSnapshotStoreError,
        match="not valid JSON",
    ):
        store.load("eu_sedia")


def test_non_object_root_is_rejected(
    tmp_path,
):
    path = tmp_path / "eu_sedia.json"

    path.write_text(
        "[]",
        encoding="utf-8",
    )

    store = HashSnapshotStore(tmp_path)

    with pytest.raises(
        HashSnapshotStoreError,
        match="root must be an object",
    ):
        store.load("eu_sedia")


def test_invalid_schema_is_rejected(
    tmp_path,
):
    path = tmp_path / "eu_sedia.json"

    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "source_id": "eu_sedia",
                "hash_algorithm": "sha256",
                "record_count": 0,
                "hashes": {},
            }
        ),
        encoding="utf-8",
    )

    store = HashSnapshotStore(tmp_path)

    with pytest.raises(
        HashSnapshotStoreError,
        match="unsupported hash snapshot schema",
    ):
        store.load("eu_sedia")


def test_source_mismatch_is_rejected(
    tmp_path,
):
    path = tmp_path / "eu_sedia.json"

    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_id": "other",
                "hash_algorithm": "sha256",
                "record_count": 0,
                "hashes": {},
            }
        ),
        encoding="utf-8",
    )

    store = HashSnapshotStore(tmp_path)

    with pytest.raises(
        HashSnapshotStoreError,
        match="source_id mismatch",
    ):
        store.load("eu_sedia")


def test_algorithm_mismatch_is_rejected(
    tmp_path,
):
    path = tmp_path / "eu_sedia.json"

    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_id": "eu_sedia",
                "hash_algorithm": "sha1",
                "record_count": 0,
                "hashes": {},
            }
        ),
        encoding="utf-8",
    )

    store = HashSnapshotStore(tmp_path)

    with pytest.raises(
        HashSnapshotStoreError,
        match="unsupported hash algorithm",
    ):
        store.load("eu_sedia")


def test_invalid_loaded_hashes_are_rejected(
    tmp_path,
):
    path = tmp_path / "eu_sedia.json"

    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_id": "eu_sedia",
                "hash_algorithm": "sha256",
                "record_count": 1,
                "hashes": {
                    "grant-a": "invalid",
                },
            }
        ),
        encoding="utf-8",
    )

    store = HashSnapshotStore(tmp_path)

    with pytest.raises(
        HashSnapshotStoreError,
        match="contains invalid hashes",
    ):
        store.load("eu_sedia")


def test_record_count_mismatch_is_rejected(
    tmp_path,
):
    path = tmp_path / "eu_sedia.json"

    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_id": "eu_sedia",
                "hash_algorithm": "sha256",
                "record_count": 2,
                "hashes": {
                    "grant-a": HASH_A,
                },
            }
        ),
        encoding="utf-8",
    )

    store = HashSnapshotStore(tmp_path)

    with pytest.raises(
        HashSnapshotStoreError,
        match="record_count mismatch",
    ):
        store.load("eu_sedia")


def test_temporary_files_are_not_left_behind(
    tmp_path,
):
    store = HashSnapshotStore(tmp_path)

    store.save(
        "eu_sedia",
        {
            "grant-a": HASH_A,
        },
    )

    assert sorted(
        path.name
        for path in tmp_path.iterdir()
    ) == [
        "eu_sedia.json",
    ]
