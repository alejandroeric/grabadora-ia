"""Tests de la transcripción (Groq/Whisper), con la red mockeada."""
import io

from services import groq_client


def test_groq_transcribe_calls_api(monkeypatch):
    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"text": "  transcripto de prueba  "}

    monkeypatch.setattr(groq_client.httpx, "post", lambda *a, **k: FakeResp())
    out = groq_client.transcribe(b"audio-bytes", "seg.webm")
    assert out == "transcripto de prueba"


def test_transcribe_route(client, monkeypatch):
    monkeypatch.setattr(groq_client, "transcribe", lambda *a, **k: "hola mundo")
    data = {"audio": (io.BytesIO(b"fake-audio"), "seg.webm")}
    res = client.post("/api/transcribe", data=data, content_type="multipart/form-data")
    assert res.status_code == 200
    assert res.get_json()["text"] == "hola mundo"


def test_transcribe_requires_file(client):
    res = client.post("/api/transcribe", data={}, content_type="multipart/form-data")
    assert res.status_code == 400


def test_transcribe_rejects_empty_audio(client):
    data = {"audio": (io.BytesIO(b""), "seg.webm")}
    res = client.post("/api/transcribe", data=data, content_type="multipart/form-data")
    assert res.status_code == 400
