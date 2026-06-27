"""Capa de datos: soporta SQLite (dev local) y PostgreSQL (Neon en prod).

El backend se elige según Config.DATABASE_URL:
- vacío  -> SQLite en el archivo db_path (con WAL + foreign keys).
- postgres:// o postgresql:// -> PostgreSQL.

Las funciones reciben db_path para mantener compatibilidad con SQLite y los
tests; en Postgres ese argumento se ignora (se usa la URL de conexión).
"""
import os
import sqlite3

from config import Config

# Normaliza la URL (psycopg prefiere el prefijo postgresql://).
DATABASE_URL = Config.DATABASE_URL
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

IS_POSTGRES = DATABASE_URL.startswith("postgresql://")

if IS_POSTGRES:  # se importa solo si hace falta
    import psycopg
    from psycopg.rows import dict_row

SCHEMA_SQLITE = os.path.join(os.path.dirname(__file__), "schema.sql")
SCHEMA_POSTGRES = os.path.join(os.path.dirname(__file__), "schema_postgres.sql")


def _q(sql):
    """Adapta los placeholders: ? (SQLite) -> %s (Postgres)."""
    return sql.replace("?", "%s") if IS_POSTGRES else sql


def _to_dict(row):
    """Normaliza una fila a dict, con created_at siempre como texto."""
    d = dict(row)
    if d.get("created_at") is not None and not isinstance(d["created_at"], str):
        d["created_at"] = str(d["created_at"])
    return d


def get_connection(db_path):
    """Abre una conexión al backend activo."""
    if IS_POSTGRES:
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path, schema_path=None):
    """Crea las tablas si no existen, con el esquema del backend activo."""
    path = schema_path or (SCHEMA_POSTGRES if IS_POSTGRES else SCHEMA_SQLITE)
    with open(path, "r", encoding="utf-8") as f:
        schema = f.read()
    conn = get_connection(db_path)
    try:
        with conn:
            if IS_POSTGRES:
                with conn.cursor() as cur:
                    for stmt in (s.strip() for s in schema.split(";")):
                        if stmt:
                            cur.execute(stmt)
            else:
                conn.executescript(schema)
    finally:
        conn.close()


def save_session(db_path, title, transcript, messages=None):
    """Guarda una sesión y su historial de chat. Devuelve el id."""
    messages = messages or []
    conn = get_connection(db_path)
    try:
        with conn:
            sql = "INSERT INTO sessions (title, transcript) VALUES (?, ?)"
            if IS_POSTGRES:
                sql += " RETURNING id"
            cur = conn.execute(_q(sql), (title, transcript))
            session_id = cur.fetchone()["id"] if IS_POSTGRES else cur.lastrowid
            for m in messages:
                conn.execute(
                    _q("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)"),
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
            "SELECT id, title, created_at FROM sessions ORDER BY created_at DESC, id DESC"
        ).fetchall()
        return [_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_session(db_path, session_id):
    """Devuelve una sesión con su transcript y sus mensajes, o None."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            _q("SELECT id, title, transcript, created_at FROM sessions WHERE id = ?"),
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        session = _to_dict(row)
        msgs = conn.execute(
            _q("SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY id"),
            (session_id,),
        ).fetchall()
        session["messages"] = [_to_dict(m) for m in msgs]
        return session
    finally:
        conn.close()


def delete_session(db_path, session_id):
    """Borra una sesión (y sus mensajes por cascade). True si existía."""
    conn = get_connection(db_path)
    try:
        with conn:
            cur = conn.execute(_q("DELETE FROM sessions WHERE id = ?"), (session_id,))
            return cur.rowcount > 0
    finally:
        conn.close()
