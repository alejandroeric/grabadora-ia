"""App Flask: capa web. Define las rutas y delega la lógica a db / services.

No tiene lógica de SQLite ni de IA adentro: solo orquesta.
"""
from flask import Flask, jsonify, render_template, request

from config import Config
from db import (
    delete_session,
    get_session,
    init_db,
    list_sessions,
    save_session,
)
from services import anthropic_client
from validation import ValidationError, validate_chat_input, validate_session_input


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    init_db(app.config["DATABASE_PATH"])

    def db_path():
        return app.config["DATABASE_PATH"]

    # --- Página principal ---
    @app.get("/")
    def index():
        return render_template("index.html")

    # --- Chat con Claude sobre el transcript (sin persistir) ---
    @app.post("/api/chat")
    def chat():
        try:
            data = validate_chat_input(request.get_json(silent=True))
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        try:
            reply = anthropic_client.ask(
                transcript=data["transcript"],
                question=data["question"],
                history=data["messages"],
            )
        except Exception:
            return jsonify(
                {"error": "No se pudo contactar a la IA. Revisá la API key del servidor."}
            ), 502
        return jsonify({"reply": reply})

    # --- Guardar una sesión en SQLite ---
    @app.post("/api/sessions")
    def create_session():
        try:
            data = validate_session_input(request.get_json(silent=True))
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        session_id = save_session(
            db_path(), data["title"], data["transcript"], data["messages"]
        )
        return jsonify({"id": session_id}), 201

    # --- Listar sesiones guardadas ---
    @app.get("/api/sessions")
    def get_sessions():
        return jsonify(list_sessions(db_path()))

    # --- Leer una sesión completa ---
    @app.get("/api/sessions/<int:session_id>")
    def read_session(session_id):
        session = get_session(db_path(), session_id)
        if session is None:
            return jsonify({"error": "Sesión no encontrada."}), 404
        return jsonify(session)

    # --- Borrar una sesión ---
    @app.delete("/api/sessions/<int:session_id>")
    def remove_session(session_id):
        if not delete_session(db_path(), session_id):
            return jsonify({"error": "Sesión no encontrada."}), 404
        return jsonify({"ok": True})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
