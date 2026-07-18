"""
tests/ai_pipeline_tests/test_normalizer.py
==========================================
Testovi za preprocessing sloj AI pipeline-a (bez vanjskih servisa).
"""

from ai_core.rag_pipeline.normalizer import Normalizer


def test_clean_text_collapses_whitespace():
    assert Normalizer.clean_text("  EU   fondovi \n\t BiH  ") == "EU fondovi BiH"


def test_clean_text_empty():
    assert Normalizer.clean_text("   ") == ""


def test_normalize_date_iso():
    assert Normalizer.normalize_date("2026-04-30") == "2026-04-30"


def test_normalize_date_datetime():
    assert Normalizer.normalize_date("2026-04-30T16:00:00") == "2026-04-30"


def test_normalize_date_invalid_passthrough():
    # Neispravan datum se vraća netaknut (bez exceptiona)
    assert Normalizer.normalize_date("uskoro") == "uskoro"
