"""
Shared test fixtures.

Each test run points the app at a fresh temp SQLite file so tests never
touch the real data/database/wild_duck_farm.db used by the desktop app.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure `app` package is importable when running `pytest` from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch, tmp_path):
    """Point the app at a throwaway SQLite DB for every test."""
    db_file = tmp_path / "test_wild_duck_farm.db"
    monkeypatch.setenv("WDF_DATABASE_URL", f"sqlite:///{db_file}")

    # Reset cached engine/session singletons so the new URL takes effect.
    import app.database.connection as connection
    connection._engine = None
    connection._SessionFactory = None
    monkeypatch.setattr(connection, "DATABASE_URL", f"sqlite:///{db_file}", raising=False)

    from app.database.connection import init_database
    init_database()
    yield
