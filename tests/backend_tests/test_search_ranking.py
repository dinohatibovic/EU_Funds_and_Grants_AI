"""Deterministic tests for the search quality reranker."""

from backend.app.api.search import (
    _grant_quality_score,
    _rerank_search_results,
)


def _metadata(**overrides):
    metadata = {
        "title": "Program podrške",
        "category": "Federalni",
        "status": "verified",
        "relevance": "medium",
        "url": "https://example.org/program",
        "verified_score": 50,
        "source_priority": 50,
    }
    metadata.update(overrides)
    return metadata


def _score(metadata):
    return _grant_quality_score(
        "neutralan upit",
        metadata,
        "Neutralni opis programa",
    )


def test_verified_status_is_explicitly_rewarded():
    verified = _score(
        _metadata(status="verified")
    )
    unverified = _score(
        _metadata(status="neprovjereno")
    )

    assert verified > unverified


def test_closed_status_is_penalized():
    verified = _score(
        _metadata(status="verified")
    )
    closed = _score(
        _metadata(status="zatvoren")
    )

    assert verified > closed


def test_verified_score_improves_quality_score():
    low = _score(
        _metadata(verified_score=20)
    )
    high = _score(
        _metadata(verified_score=95)
    )

    assert high > low


def test_source_priority_improves_quality_score():
    low = _score(
        _metadata(source_priority=20)
    )
    high = _score(
        _metadata(source_priority=95)
    )

    assert high > low


def test_invalid_ranking_values_use_neutral_defaults():
    neutral = _score(
        _metadata(
            verified_score=50,
            source_priority=50,
        )
    )
    invalid = _score(
        _metadata(
            verified_score="invalid",
            source_priority=None,
        )
    )

    assert invalid == neutral


def test_ranking_values_are_clamped():
    maximum = _score(
        _metadata(
            verified_score=100,
            source_priority=100,
        )
    )
    excessive = _score(
        _metadata(
            verified_score=1000,
            source_priority=1000,
        )
    )

    assert excessive == maximum


def test_reranker_promotes_higher_quality_metadata():
    documents = [
        "Isti neutralni dokument",
        "Isti neutralni dokument",
    ]
    metadatas = [
        _metadata(
            title="Niži score",
            verified_score=20,
        ),
        _metadata(
            title="Viši score",
            verified_score=95,
        ),
    ]

    _, ranked_metadata = _rerank_search_results(
        "neutralan upit",
        documents,
        metadatas,
        limit=2,
    )

    assert ranked_metadata[0]["title"] == "Viši score"
    assert ranked_metadata[1]["title"] == "Niži score"


def test_equal_scores_preserve_chroma_order():
    documents = [
        "Prvi",
        "Drugi",
        "Treći",
    ]
    metadatas = [
        _metadata(title="Prvi"),
        _metadata(title="Drugi"),
        _metadata(title="Treći"),
    ]

    ranked_documents, _ = _rerank_search_results(
        "neutralan upit",
        documents,
        metadatas,
        limit=3,
    )

    assert ranked_documents == documents


def test_reranker_respects_limit():
    documents = [
        "Prvi",
        "Drugi",
        "Treći",
    ]
    metadatas = [
        _metadata()
        for _ in documents
    ]

    ranked_documents, ranked_metadata = (
        _rerank_search_results(
            "neutralan upit",
            documents,
            metadatas,
            limit=2,
        )
    )

    assert len(ranked_documents) == 2
    assert len(ranked_metadata) == 2
