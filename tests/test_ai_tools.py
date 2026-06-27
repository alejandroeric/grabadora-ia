"""Tests de las herramientas IA nuevas: pulir, tareas, cuestionario, cuadro."""
from unittest.mock import MagicMock

from services import anthropic_client


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


# --- Capa de IA ---
def test_polish_returns_text():
    out = anthropic_client.polish_transcript("hola q tal", client=_fake_client("Hola, ¿qué tal?"))
    assert out == "Hola, ¿qué tal?"


def test_extract_tasks_parses_json():
    fake = _fake_client('[{"task": "Leer cap 3", "due": "martes"}, {"task": "", "due": "x"}]')
    tasks = anthropic_client.extract_tasks("t", client=fake)
    assert len(tasks) == 1
    assert tasks[0]["task"] == "Leer cap 3"
    assert tasks[0]["due"] == "martes"


def test_generate_quiz_normalizes_correct_index():
    fake = _fake_client(
        '[{"question": "¿2+2?", "options": ["3", "4"], "correct": 9, "explanation": "obvio"}]'
    )
    quiz = anthropic_client.generate_quiz("t", client=fake)
    assert quiz[0]["correct"] == 1  # se recorta al rango válido
    assert quiz[0]["options"] == ["3", "4"]


def test_comparison_table_parses():
    fake = _fake_client('{"title": "Comparación", "headers": ["A", "B"], "rows": [["1", "2"]]}')
    table = anthropic_client.comparison_table("t", client=fake)
    assert table["headers"] == ["A", "B"]
    assert table["rows"] == [["1", "2"]]


# --- Rutas (IA mockeada) ---
def test_polish_route(client, monkeypatch):
    monkeypatch.setattr(anthropic_client, "polish_transcript", lambda *a, **k: "pulido")
    res = client.post("/api/polish", json={"transcript": "hola"})
    assert res.status_code == 200
    assert res.get_json()["polished"] == "pulido"


def test_tasks_route(client, monkeypatch):
    monkeypatch.setattr(
        anthropic_client, "extract_tasks", lambda *a, **k: [{"task": "x", "due": "hoy"}]
    )
    res = client.post("/api/tasks", json={"transcript": "hola"})
    assert res.status_code == 200
    assert res.get_json()["tasks"][0]["task"] == "x"


def test_quiz_route(client, monkeypatch):
    monkeypatch.setattr(
        anthropic_client,
        "generate_quiz",
        lambda *a, **k: [{"question": "q", "options": ["a", "b"], "correct": 0, "explanation": ""}],
    )
    res = client.post("/api/quiz", json={"transcript": "hola"})
    assert res.status_code == 200
    assert len(res.get_json()["quiz"]) == 1


def test_table_route(client, monkeypatch):
    monkeypatch.setattr(
        anthropic_client,
        "comparison_table",
        lambda *a, **k: {"title": "T", "headers": ["A"], "rows": [["1"]]},
    )
    res = client.post("/api/table", json={"transcript": "hola"})
    assert res.status_code == 200
    assert res.get_json()["table"]["headers"] == ["A"]


def test_tools_require_transcript(client):
    assert client.post("/api/polish", json={"transcript": ""}).status_code == 400
    assert client.post("/api/quiz", json={"transcript": ""}).status_code == 400
