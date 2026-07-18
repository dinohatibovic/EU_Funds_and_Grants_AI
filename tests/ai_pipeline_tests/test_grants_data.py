"""
tests/ai_pipeline_tests/test_grants_data.py
===========================================
Validacija integriteta data/grants.json — izvora istine za RAG ingestion.
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

GRANTS_FILE = Path(__file__).resolve().parents[2] / "data" / "grants.json"


@pytest.fixture(scope="module")
def grants():
    with open(GRANTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def test_grants_file_is_valid_json_list(grants):
    assert isinstance(grants, list)
    assert len(grants) > 0


def test_all_grants_have_required_fields(grants):
    for g in grants:
        for field in ("id", "title", "category", "description", "url"):
            assert field in g, f"Grant {g.get('id', '?')} nema polje '{field}'"
        assert g["title"].strip(), f"Grant {g['id']} ima prazan naslov"


def test_grant_ids_are_unique(grants):
    ids = [g["id"] for g in grants]
    assert len(ids) == len(set(ids)), "Duplikat ID-eva u grants.json!"


def test_deadlines_are_null_or_iso_format(grants):
    for g in grants:
        deadline = g.get("deadline")
        if deadline is None:
            continue
        datetime.strptime(deadline, "%Y-%m-%d")  # baca ValueError ako nije ISO
