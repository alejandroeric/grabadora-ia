"""Tests de las herramientas IA: plantillas, resumen, traducción y mapa mental."""
from unittest.mock import MagicMock

import pytest

import templates_ia
from services import anthropic_client
from validation import (
    ValidationError,
    validate_mindmap_input,
    validate_summary_input,
    validate_translate_input,
)


class _FakeBlock:
    def __init__(self, text):
        self.text = text


class _FakeResponse:
    def __init__(self, text):
        self.content = [_FakeBlock(text)]


def _fake_client(text):
    fake = MagicMock()
    fake.messages.create.return_value = _FakeResponse(text)
    return fake


# --- Plantillas ---
def test_summary_templates_cover_all_types():
    assert set(templates_ia.SUMMARY_TEMPLATES) == set(templates_ia.SUMMARY_TYPES)


# --- Capa de IA (con mock) ---
def test_generate_summary_returns_text():
    fake = _fake_client("TEMA PRINCIPAL: la célula")
    out = anthropic_client.generate_summary("transcript", "clase", client=fake)
    assert "TEMA PRINCIPAL" in out
    fake.messages.create.assert_called_once()


def test_translate_returns_text():
    fake = _fake_client("The cell is the unit of life.")
    out = anthropic_client.translate("La célula es la unidad de la vida.", "inglés", client=fake)
    assert "cell" in out


def test_mindmap_strips_code_fences():
    fake = _fake_client("```mermaid\nmindmap\n  root((Tema))\n```")
    out = anthropic_client.mindmap("transcript", client=fake)
    assert out.startswith("mindmap")
    assert "```" not in out


def test_glossary_is_injected_into_system_prompt():
    fake = _fake_client("ok")
    anthropic_client.generate_summary("t", "clase", glossary="mitocondria", client=fake)
    system = fake.messages.create.call_args.kwargs["system"]
    assert "mitocondria" in system


# --- Validación ---
def test_summary_rejects_invalid_type():
    with pytest.raises(ValidationError):
        validate_summary_input({"transcript": "t", "type": "fiesta"})


def test_summary_defaults_to_clase():
    clean = validate_summary_input({"transcript": "t"})
    assert clean["type"] == "clase"


def test_translate_requires_target():
    with pytest.raises(ValidationError):
        validate_translate_input({"transcript": "t", "target": ""})


def test_mindmap_requires_transcript():
    with pytest.raises(ValidationError):
        validate_mindmap_input({"transcript": ""})


# --- Rutas (con mock de la IA) ---
def test_summary_route(client, monkeypatch):
    monkeypatch.setattr(anthropic_client, "generate_summary", lambda *a, **k: "resumen ok")
    res = client.post("/api/summary", json={"transcript": "hola", "type": "clase"})
    assert res.status_code == 200
    assert res.get_json()["summary"] == "resumen ok"


def test_translate_route(client, monkeypatch):
    monkeypatch.setattr(anthropic_client, "translate", lambda *a, **k: "hello")
    res = client.post("/api/translate", json={"transcript": "hola", "target": "inglés"})
    assert res.status_code == 200
    assert res.get_json()["translation"] == "hello"


def test_mindmap_route(client, monkeypatch):
    monkeypatch.setattr(anthropic_client, "mindmap", lambda *a, **k: "mindmap\n  root((X))")
    res = client.post("/api/mindmap", json={"transcript": "hola"})
    assert res.status_code == 200
    assert res.get_json()["mermaid"].startswith("mindmap")
