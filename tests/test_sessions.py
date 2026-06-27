"""Tests de la capa de datos: guardado y lectura de sesiones en SQLite."""
import db


def test_save_and_read_session(db_path):
    sid = db.save_session(db_path, "Clase de Historia", "El profe habló de la revolución.")
    assert isinstance(sid, int)

    session = db.get_session(db_path, sid)
    assert session["title"] == "Clase de Historia"
    assert "revolución" in session["transcript"]
    assert session["messages"] == []


def test_save_session_with_messages(db_path):
    msgs = [
        {"role": "user", "content": "¿Qué tareas dejó?"},
        {"role": "assistant", "content": "Leer el capítulo 3."},
    ]
    sid = db.save_session(db_path, "Clase", "Transcript de ejemplo", msgs)

    session = db.get_session(db_path, sid)
    assert len(session["messages"]) == 2
    assert session["messages"][0]["role"] == "user"
    assert session["messages"][1]["content"] == "Leer el capítulo 3."


def test_list_sessions(db_path):
    db.save_session(db_path, "A", "t1")
    db.save_session(db_path, "B", "t2")

    sessions = db.list_sessions(db_path)
    assert len(sessions) == 2
    assert {s["title"] for s in sessions} == {"A", "B"}
    # El listado no trae el transcript completo
    assert "transcript" not in sessions[0]


def test_delete_session_cascades_messages(db_path):
    sid = db.save_session(db_path, "X", "t", [{"role": "user", "content": "hola"}])
    assert db.delete_session(db_path, sid) is True
    assert db.get_session(db_path, sid) is None


def test_delete_missing_session_returns_false(db_path):
    assert db.delete_session(db_path, 999) is False


def test_get_missing_session_returns_none(db_path):
    assert db.get_session(db_path, 999) is None
