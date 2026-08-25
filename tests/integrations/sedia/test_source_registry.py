from pathlib import Path

import pytest

from backend.app.models.grant_source import (
    SourceAuthorityLevel,
)
from backend.app.services.source_registry_service import (
    SourceRegistryService,
)


REGISTRY = Path(
    "backend/app/data/source_registry/sources.json"
)


def test_registry_loads_all_sources() -> None:
    service = SourceRegistryService(REGISTRY)
    sources = service.load()

    assert len(sources) == 11
    assert len(sources) == len(
        {source.source_id for source in sources}
    )


def test_sedia_is_official_api_source() -> None:
    service = SourceRegistryService(REGISTRY)
    source = service.get("eu_sedia")

    assert source.authority_level == (
        SourceAuthorityLevel.OFFICIAL_PUBLISHER
    )
    assert source.access_method == "sedia_api"
    assert source.requires_manual_review is False


def test_other_sources_require_review() -> None:
    service = SourceRegistryService(REGISTRY)

    sources = [
        source
        for source in service.enabled_sources()
        if source.source_id != "eu_sedia"
    ]

    assert len(sources) == 10
    assert all(
        source.requires_manual_review
        for source in sources
    )


def test_unknown_source_raises_key_error() -> None:
    service = SourceRegistryService(REGISTRY)

    with pytest.raises(KeyError):
        service.get("does_not_exist")
