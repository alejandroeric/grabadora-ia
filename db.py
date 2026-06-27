"""Capa de datos: todo lo que toca SQLite vive acá.

Cada conexión activa WAL mode y foreign keys (requisitos del proyecto).
Las funciones reciben db_path explícito para que los tests puedan usar
una base temporal sin tocar la real.
"""
import os
import sqlite3

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_connection(db_path):
    """Abre una conexión con WAL mode y foreign keys habilitados."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path, schema_path=SCHEMA_PATH):
    """Crea las tablas si no existen, a partir de schema.sql."""
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()
    conn = get_connection(db_path)
    try:
        with conn:
            conn.executescript(schema)
    finally:
        conn.close()


def save_session(db_path, title, transcript, messages=None):
    """Guarda una sesión y, opcionalmente, su historial de chat.

    Devuelve el id de la sesión creada.
    """
    messages = messages or []
    conn = get_connection(db_path)
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO sessions (title, transcript) VALUES (?, ?)",
                (title, transcript),
            )
            session_id = cur.lastrowid
            for m in messages:
                conn.execute(
                    "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                    (session_id, m["role"], m["content"]),
                )
        return session_id
    finally:
        conn.close()


def list_sessions(db_path):
    """Lista las sesiones guardadas (sin el transcript completo)."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT id, title, created_at FROM sessions "
            "ORDER BY datetime(created_at) DESC, id DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_session(db_path, session_id):
    """Devuelve una sesión con su transcript y sus mensajes, o None."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT id, title, transcript, created_at FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        session = dict(row)
        msgs = conn.execute(
            "SELECT role, content, created_at FROM messages "
            "WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        session["messages"] = [dict(m) for m in msgs]
        return session
    finally:
        conn.close()


def delete_session(db_path, session_id):
    """Borra una sesión (y sus mensajes por cascade). Devuelve True si existía."""
    conn = get_connection(db_path)
    try:
        with conn:
            cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return cur.rowcount > 0
    finally:
        conn.close()
