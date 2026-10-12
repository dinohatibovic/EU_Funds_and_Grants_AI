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


def test_bm25_normalizes_startup_inflections():
    from ai_core.vector_store.bm25_index import (
        tokenize,
    )

    assert tokenize("startup") == ["startup"]
    assert tokenize("startupe") == ["startup"]
    assert tokenize("startupa") == ["startup"]
    assert tokenize("startupima") == ["startup"]


def test_bm25_normalizes_tesanj_inflections():
    from ai_core.vector_store.bm25_index import (
        tokenize,
    )

    assert tokenize("Tešanj") == ["tesanj"]
    assert tokenize("Tešnju") == ["tesanj"]
    assert tokenize("Tesanj") == ["tesanj"]
    assert tokenize("Tesnju") == ["tesanj"]


def test_bm25_removes_generic_bosnian_search_words():
    from ai_core.vector_store.bm25_index import (
        tokenize,
    )

    assert tokenize(
        "Koji grantovi postoje za startupe u BiH?"
    ) == [
        "startup",
        "bih",
    ]

    assert tokenize(
        "grantovi za obrt u Tešnju"
    ) == [
        "obrt",
        "tesanj",
    ]

def test_query_intent_normalizes_startup_and_tesanj():
    from backend.app.api.search import (
        _parse_query_intent,
    )

    startup = _parse_query_intent(
        "Koji grantovi postoje za startupe u BiH?"
    )
    tesanj = _parse_query_intent(
        "grantovi za obrt u Tešnju"
    )
    tesnju = _parse_query_intent(
        "grantovi za obrt u Tesnju"
    )

    assert startup == {
        "beneficiaries": {"startup"},
        "locations": {"bih"},
        "sectors": set(),
    }

    assert tesanj == {
        "beneficiaries": {"obrt"},
        "locations": {
            "tesanj",
            "zdk",
            "bih",
        },
        "sectors": set(),
    }

    assert tesnju == tesanj


def test_query_intent_treats_firm_forms_as_sme():
    from backend.app.api.search import (
        _parse_query_intent,
    )

    queries = (
        "digitalizacija firme u ZDK",
        "grant za firmu u ZDK",
        "podrška firmi iz BiH",
        "grantovi za firme u BiH",
        "podrška firmama u ZDK",
    )

    for query in queries:
        intent = _parse_query_intent(query)

        assert "sme" in intent["beneficiaries"]


def test_startup_bih_intent_outranks_health():
    query = "Koji grantovi postoje za startupe u BiH?"

    startup_metadata = _metadata(
        title="EIC Accelerator",
        category="Startup",
        regions='["BiH"]',
        beneficiary_types='["SME", "startup"]',
        sectors='["digitalization"]',
        verified_score=95,
    )
    health_metadata = _metadata(
        title="Horizont Evropa - Zdravstvo",
        category="Istraživanje",
        regions='["BiH"]',
        beneficiary_types='["SME"]',
        sectors='["health"]',
        verified_score=95,
    )

    startup_score = _grant_quality_score(
        query,
        startup_metadata,
        "EU finansiranje inovativnih startupa.",
    )
    health_score = _grant_quality_score(
        query,
        health_metadata,
        "Zdravstvena istraživanja za SME.",
    )

    assert startup_score > health_score


def test_obrt_tesanj_intent_outranks_life():
    query = "grantovi za obrt u Tešnju"

    local_metadata = _metadata(
        title="ZEDA pozivi za obrte",
        category="ZDK",
        regions='["Tešanj", "ZDK", "BiH"]',
        beneficiary_types='["obrt", "SME"]',
        sectors='["digitalization"]',
        status="rolling",
    )
    life_metadata = _metadata(
        title="LIFE Programme",
        category="Okoliš",
        regions='["BiH"]',
        beneficiary_types='["SME"]',
        sectors='["environment"]',
        verified_score=95,
    )

    local_score = _grant_quality_score(
        query,
        local_metadata,
        "Podrška obrtima i MSP u Tešnju.",
    )
    life_score = _grant_quality_score(
        query,
        life_metadata,
        "Okolišni i klimatski program za SME.",
    )

    assert local_score > life_score


def test_agriculture_intent_outranks_digital():
    query = "poticaji za poljoprivredu u BiH"

    agriculture_metadata = _metadata(
        title="FMPVS poljoprivredne podrške",
        category="Poljoprivreda",
        regions='["FBiH", "BiH"]',
        beneficiary_types='["SME"]',
        sectors='["agriculture"]',
    )
    digital_metadata = _metadata(
        title="Digitalizacija MSP",
        category="Digital",
        regions='["BiH"]',
        beneficiary_types='["SME"]',
        sectors='["digitalization"]',
    )

    agriculture_score = _grant_quality_score(
        query,
        agriculture_metadata,
        "Poljoprivreda i ruralni razvoj.",
    )
    digital_score = _grant_quality_score(
        query,
        digital_metadata,
        "Digitalizacija i softver za MSP.",
    )

    assert agriculture_score > digital_score


def test_reranker_places_startup_above_generic_programs():
    query = "Koji grantovi postoje za startupe u BiH?"

    documents = [
        "Zdravstvena istraživanja za SME.",
        "Okolišni i klimatski program za SME.",
        "EU finansiranje inovativnih startupa.",
    ]
    metadatas = [
        _metadata(
            title="Horizont Evropa - Zdravstvo",
            category="Istraživanje",
            regions='["BiH"]',
            beneficiary_types='["SME"]',
            sectors='["health"]',
            verified_score=95,
        ),
        _metadata(
            title="LIFE Programme",
            category="Okoliš",
            regions='["BiH"]',
            beneficiary_types='["SME"]',
            sectors='["environment"]',
            verified_score=95,
        ),
        _metadata(
            title="EIC Accelerator",
            category="Startup",
            regions='["BiH"]',
            beneficiary_types='["SME", "startup"]',
            sectors='["digitalization"]',
            verified_score=95,
        ),
    ]

    _, ranked_metadata = _rerank_search_results(
        query,
        documents,
        metadatas,
        limit=3,
    )

    titles = [
        metadata["title"]
        for metadata in ranked_metadata
    ]

    assert titles[0] == "EIC Accelerator"
    assert titles.index(
        "EIC Accelerator"
    ) < titles.index(
        "Horizont Evropa - Zdravstvo"
    )
    assert titles.index(
        "EIC Accelerator"
    ) < titles.index(
        "LIFE Programme"
    )
