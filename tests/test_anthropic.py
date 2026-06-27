"""Tests de la integración con Anthropic (con mock, sin llamar a la API real)."""
from unittest.mock import MagicMock

from services import anthropic_client


class _FakeBlock:
    def __init__(self, text):
        self.text = text


class _FakeResponse:
    def __init__(self, text):
        self.content = [_FakeBlock(text)]


def test_ask_uses_injected_client_and_returns_text():
    fake = MagicMock()
    fake.messages.create.return_value = _FakeResponse("Resumen: punto 1, 2 y 3.")

    result = anthropic_client.ask(
        transcript="El profe explicó la fotosíntesis.",
        question="Resumime en 3 puntos",
        client=fake,
    )

    assert result == "Resumen: punto 1, 2 y 3."
    fake.messages.create.assert_called_once()


def test_ask_passes_model_and_question_to_api():
    fake = MagicMock()
    fake.messages.create.return_value = _FakeResponse("ok")

    anthropic_client.ask("transcript", "mi pregunta", client=fake)

    kwargs = fake.messages.create.call_args.kwargs
    assert "model" in kwargs
    assert kwargs["messages"][-1]["content"] == "mi pregunta"


def test_build_messages_includes_transcript_and_question():
    messages = anthropic_client.build_messages("CONTENIDO_CLASE", [], "¿Qué tareas?")
    joined = " ".join(m["content"] for m in messages)
    assert "CONTENIDO_CLASE" in joined
    assert "¿Qué tareas?" in joined
    assert messages[-1]["role"] == "user"


def test_chat_route_with_mocked_ia(client, monkeypatch):
    monkeypatch.setattr(anthropic_client, "ask", lambda **kwargs: "respuesta mockeada")

    res = client.post(
        "/api/chat",
        json={"transcript": "hola mundo", "question": "¿qué dije?"},
    )

    assert res.status_code == 200
    assert res.get_json()["reply"] == "respuesta mockeada"


def test_chat_route_validates_input(client):
    res = client.post("/api/chat", json={"transcript": "", "question": ""})
    assert res.status_code == 400
    assert "error" in res.get_json()
