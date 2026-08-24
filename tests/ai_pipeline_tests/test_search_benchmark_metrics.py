"""Tests for offline search benchmark metrics."""

import pytest

from tests.benchmarks.evaluate_search_results import (
    discounted_cumulative_gain,
    hit_rate_at_k,
    ndcg_at_k,
    ranked_ids_from_response,
    reciprocal_rank_at_k,
)


def test_ranked_ids_preserve_api_order():
    response = {
        "metadatas": [
            [
                {"grant_id": "grant_a"},
                {"id": "grant_b"},
                {"title": "Bez ID-a"},
            ]
        ]
    }

    assert ranked_ids_from_response(response) == [
        "grant_a",
        "grant_b",
    ]


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"metadatas": None},
        {"metadatas": []},
        {"metadatas": {}},
    ],
)
def test_ranked_ids_reject_invalid_shapes(response):
    assert ranked_ids_from_response(response) == []


def test_hit_rate_detects_relevant_top_five_result():
    assert hit_rate_at_k(
        ["other", "relevant"],
        {"relevant": 2},
        threshold=2,
        k=5,
    ) == 1.0


def test_hit_rate_respects_threshold():
    assert hit_rate_at_k(
        ["partial"],
        {"partial": 1},
        threshold=2,
        k=5,
    ) == 0.0


def test_reciprocal_rank_uses_first_relevant_result():
    assert reciprocal_rank_at_k(
        ["other", "partial", "relevant"],
        {
            "partial": 1,
            "relevant": 3,
        },
        threshold=2,
        k=10,
    ) == pytest.approx(1 / 3)


def test_reciprocal_rank_respects_cutoff():
    ranked_ids = [
        f"grant_{index}"
        for index in range(1, 11)
    ]

    assert reciprocal_rank_at_k(
        ranked_ids,
        {"grant_10": 3},
        threshold=2,
        k=5,
    ) == 0.0

    assert reciprocal_rank_at_k(
        ranked_ids,
        {"grant_10": 3},
        threshold=2,
        k=10,
    ) == pytest.approx(0.1)


def test_dcg_is_zero_for_zero_grades():
    assert discounted_cumulative_gain(
        [0, 0, 0]
    ) == 0.0


def test_ndcg_is_one_for_ideal_order():
    relevance = {
        "best": 3,
        "good": 2,
        "partial": 1,
    }

    assert ndcg_at_k(
        ["best", "good", "partial"],
        relevance,
        k=10,
    ) == pytest.approx(1.0)


def test_ndcg_penalizes_reversed_order():
    relevance = {
        "best": 3,
        "good": 2,
        "partial": 1,
    }

    score = ndcg_at_k(
        ["partial", "good", "best"],
        relevance,
        k=10,
    )

    assert 0.0 < score < 1.0


def test_ndcg_is_zero_without_judgments():
    assert ndcg_at_k(
        ["grant_a"],
        {},
        k=10,
    ) == 0.0
