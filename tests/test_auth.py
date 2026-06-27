"""Tests de seguridad: login por contraseña y protección de rutas."""
import pytest

from app import create_app
from services import anthropic_client


@pytest.fixture
def auth_client(tmp_path):
    app = create_app(
        {
            "DATABASE_PATH": str(tmp_path / "auth.db"),
            "APP_PASSWORD": "secreto",
            "SECRET_KEY": "test-key",
            "TESTING": True,
        }
    )
    return app.test_client()


def test_index_redirects_to_login_when_not_authed(auth_client):
    res = auth_client.get("/")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_api_returns_401_when_not_authed(auth_client):
    res = auth_client.post("/api/chat", json={"transcript": "t", "question": "q"})
    assert res.status_code == 401


def test_login_with_wrong_password_fails(auth_client):
    res = auth_client.post("/login", data={"password": "incorrecta"})
    assert res.status_code == 401


def test_login_then_access_granted(auth_client, monkeypatch):
    monkeypatch.setattr(anthropic_client, "ask", lambda **kwargs: "respuesta ok")
    login = auth_client.post("/login", data={"password": "secreto"})
    assert login.status_code == 302

    res = auth_client.post("/api/chat", json={"transcript": "t", "question": "q"})
    assert res.status_code == 200
    assert res.get_json()["reply"] == "respuesta ok"


def test_auth_disabled_allows_open_access(client):
    """Sin APP_PASSWORD (fixture client por defecto), la app queda abierta."""
    assert client.get("/").status_code == 200
