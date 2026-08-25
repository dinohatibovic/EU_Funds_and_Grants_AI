import asyncio
from unittest.mock import AsyncMock, MagicMock

from backend.app import main as app_module


def _run_lifespan():
    async def exercise():
        async with app_module.lifespan(
            app_module.app
        ):
            return None

    asyncio.run(exercise())


def test_lifespan_preserves_startup_order(
    monkeypatch,
):
    calls = []

    monkeypatch.setenv(
        "JWT_SECRET",
        "test-secret",
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test",
    )

    monkeypatch.setattr(
        app_module,
        "init_user_db",
        lambda: calls.append("init_user_db"),
    )
    monkeypatch.setattr(
        app_module.ai_services,
        "load_grants_cache",
        lambda: calls.append("load_grants_cache"),
    )
    monkeypatch.setattr(
        app_module.ai_services,
        "init_ai_clients",
        lambda: calls.append("init_ai_clients"),
    )

    async def auto_ingest():
        calls.append("auto_ingest_grants")

    monkeypatch.setattr(
        app_module.ai_services,
        "auto_ingest_grants",
        auto_ingest,
    )

    _run_lifespan()

    assert calls == [
        "init_user_db",
        "load_grants_cache",
        "init_ai_clients",
        "auto_ingest_grants",
    ]


def test_lifespan_preserves_database_fallback(
    monkeypatch,
):
    calls = []

    monkeypatch.setenv(
        "JWT_SECRET",
        "test-secret",
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test",
    )

    attempts = 0

    def init_user_db():
        nonlocal attempts
        attempts += 1
        calls.append("init_user_db")

        if attempts == 1:
            raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        app_module,
        "init_user_db",
        init_user_db,
    )
    monkeypatch.setattr(
        app_module.config,
        "use_sqlite_fallback",
        lambda: calls.append(
            "use_sqlite_fallback"
        ),
    )
    monkeypatch.setattr(
        app_module.ai_services,
        "load_grants_cache",
        lambda: calls.append("load_grants_cache"),
    )
    monkeypatch.setattr(
        app_module.ai_services,
        "init_ai_clients",
        lambda: calls.append("init_ai_clients"),
    )

    auto_ingest = AsyncMock()

    monkeypatch.setattr(
        app_module.ai_services,
        "auto_ingest_grants",
        auto_ingest,
    )

    _run_lifespan()

    assert calls == [
        "init_user_db",
        "use_sqlite_fallback",
        "init_user_db",
        "load_grants_cache",
        "init_ai_clients",
    ]
    auto_ingest.assert_awaited_once_with()


def test_lifespan_keeps_ai_startup_failure_safe(
    monkeypatch,
):
    monkeypatch.setenv(
        "JWT_SECRET",
        "test-secret",
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test",
    )

    monkeypatch.setattr(
        app_module,
        "init_user_db",
        MagicMock(),
    )
    monkeypatch.setattr(
        app_module.ai_services,
        "load_grants_cache",
        MagicMock(),
    )
    monkeypatch.setattr(
        app_module.ai_services,
        "init_ai_clients",
        MagicMock(
            side_effect=RuntimeError(
                "AI unavailable"
            )
        ),
    )

    auto_ingest = AsyncMock()

    monkeypatch.setattr(
        app_module.ai_services,
        "auto_ingest_grants",
        auto_ingest,
    )

    _run_lifespan()

    auto_ingest.assert_not_awaited()
