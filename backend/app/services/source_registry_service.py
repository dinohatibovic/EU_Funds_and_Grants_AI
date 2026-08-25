"""Read-only source-registry service."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from backend.app.models.grant_source import GrantSource


class SourceRegistryService:
    """Load and validate configured grant sources."""

    def __init__(
        self,
        registry_path: Path | str,
    ) -> None:
        self.registry_path = Path(registry_path)

    def load(self):
        """Load all sources from the registry file."""

        try:
            text = self.registry_path.read_text(
                encoding="utf-8"
            )
        except OSError as exc:
            raise RuntimeError(
                "Cannot read source registry: "
                f"{self.registry_path}"
            ) from exc

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Source registry is not valid JSON"
            ) from exc

        if not isinstance(payload, list):
            raise ValueError(
                "Source registry root must be a list"
            )

        try:
            sources = [
                GrantSource.model_validate(item)
                for item in payload
            ]
        except ValidationError as exc:
            raise ValueError(
                "Source registry contains an "
                "invalid source record"
            ) from exc

        source_ids = [
            source.source_id
            for source in sources
        ]

        if len(source_ids) != len(set(source_ids)):
            raise ValueError(
                "Source registry contains duplicate "
                "source_id values"
            )

        return sources

    def enabled_sources(self):
        """Return enabled sources only."""

        return [
            source
            for source in self.load()
            if source.enabled
        ]

    def get(self, source_id: str) -> GrantSource:
        """Return one source by its stable identifier."""

        for source in self.load():
            if source.source_id == source_id:
                return source

        raise KeyError(
            f"Unknown source_id: {source_id}"
        )
