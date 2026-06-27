"""Fixtures comunes para los tests.

Cada test usa una base SQLite temporal (tmp_path), nunca la real.
"""
import os
import sys

import pytest

# Los tests SIEMPRE usan SQLite, sin importar lo que haya en el .env.
# (load_dotenv no pisa una variable ya existente, así que esto gana.)
os.environ["DATABASE_URL"] = ""
os.environ["DATABASE_PATH"] = ":memory:"

# Permite importar los módulos del proyecto (app, db, etc.) desde tests/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import db as db_module  # noqa: E402
from app import create_app  # noqa: E402


@pytest.fixture
def db_path(tmp_path):
    """Ruta a una base temporal ya inicializada con el esquema."""
    path = str(tmp_path / "test.db")
    db_module.init_db(path)
    return path


@pytest.fixture
def app(tmp_path):
    return create_app({"DATABASE_PATH": str(tmp_path / "app.db"), "TESTING": True})


@pytest.fixture
def client(app):
    return app.test_client()
