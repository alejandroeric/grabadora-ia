"""Tests de flashcards: algoritmo SM-2, capa de datos y rutas."""
from datetime import date
from unittest.mock import MagicMock

import db
from services import anthropic_client
from srs import sm2


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


# --- SM-2 ---
def test_sm2_fail_resets_repetitions():
    r = sm2(1, repetitions=5, easiness=2.5, interval_days=20)
    assert r["repetitions"] == 0
    assert r["interval_days"] == 1


def test_sm2_first_and_second_success():
    first = sm2(5, 0, 2.5, 0)
    assert first["repetitions"] == 1 and first["interval_days"] == 1
    second = sm2(5, 1, 2.5, 1)
    assert second["repetitions"] == 2 and second["interval_days"] == 6


def test_sm2_easiness_has_floor():
    r = sm2(0, 0, 1.3, 1)
    assert r["easiness"] >= 1.3


# --- Capa de datos ---
def test_save_and_list_due_flashcards(db_path):
    n = db.save_flashcards(
        db_path, [{"question": "q1", "answer": "a1"}, {"question": "q2", "answer": "a2"}]
    )
    assert n == 2
    due = db.list_due_flashcards(db_path, date.today().isoformat())
    assert len(due) == 2


def test_grade_pushes_card_out_of_due(db_path):
    db.save_flashcards(db_path, [{"question": "q", "answer": "a"}])
    cid = db.list_due_flashcards(db_path, date.today().isoformat())[0]["id"]
    assert db.get_flashcard(db_path, cid)["question"] == "q"
    db.update_flashcard_srs(db_path, cid, 1, 2.5, 6, "2999-01-01")
    due = db.list_due_flashcards(db_path, date.today().isoformat())
    assert all(c["id"] != cid for c in due)


def test_flashcard_stats(db_path):
    db.save_flashcards(db_path, [{"question": "q", "answer": "a"}])
    stats = db.flashcard_stats(db_path, date.today().isoformat())
    assert stats["total"] == 1
    assert stats["due"] == 1


# --- Generación con IA (mock) ---
def test_generate_flashcards_parses_json():
    fake = _fake_client('[{"question": "¿Qué es X?", "answer": "Y"}]')
    cards = anthropic_client.generate_flashcards("transcript", client=fake)
    assert len(cards) == 1
    assert cards[0]["question"] == "¿Qué es X?"


def test_generate_flashcards_strips_code_fences():
    fake = _fake_client('```json\n[{"question": "q", "answer": "a"}]\n```')
    cards = anthropic_client.generate_flashcards("t", client=fake)
    assert cards[0]["answer"] == "a"


# --- Rutas ---
def test_flashcards_generate_route(client, monkeypatch):
    monkeypatch.setattr(
        anthropic_client, "generate_flashcards", lambda *a, **k: [{"question": "q", "answer": "a"}]
    )
    res = client.post("/api/flashcards/generate", json={"transcript": "hola"})
    assert res.status_code == 200
    assert res.get_json()["cards"][0]["question"] == "q"


def test_flashcards_save_and_due_route(client):
    save = client.post("/api/flashcards", json={"cards": [{"question": "q", "answer": "a"}]})
    assert save.status_code == 201
    due = client.get("/api/flashcards/due")
    assert due.status_code == 200
    data = due.get_json()
    assert data["stats"]["total"] >= 1
    assert len(data["cards"]) >= 1


def test_flashcards_grade_route(client):
    client.post("/api/flashcards", json={"cards": [{"question": "q", "answer": "a"}]})
    cid = client.get("/api/flashcards/due").get_json()["cards"][0]["id"]
    res = client.post(f"/api/flashcards/{cid}/grade", json={"quality": 5})
    assert res.status_code == 200
    assert res.get_json()["interval_days"] == 1


def test_flashcards_save_rejects_empty(client):
    res = client.post("/api/flashcards", json={"cards": []})
    assert res.status_code == 400
