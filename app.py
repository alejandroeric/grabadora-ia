"""App Flask: capa web. Define las rutas y delega la lógica a db / services.

No tiene lógica de SQLite ni de IA adentro: solo orquesta.
"""
import json
from datetime import date, timedelta

from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from config import Config
from security import rate_limit, require_auth
from db import (
    delete_session,
    flashcard_stats,
    get_flashcard,
    get_session,
    init_db,
    list_due_flashcards,
    list_sessions,
    save_flashcards,
    save_session,
    update_flashcard_srs,
)
from services import anthropic_client
from srs import sm2
from validation import (
    ValidationError,
    validate_chat_input,
    validate_flashcards_gen_input,
    validate_flashcards_save_input,
    validate_grade_input,
    validate_mindmap_input,
    validate_session_input,
    validate_summary_input,
    validate_translate_input,
)


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    app.config.setdefault("PERMANENT_SESSION_LIFETIME", timedelta(days=14))
    init_db(app.config["DATABASE_PATH"])

    def db_path():
        return app.config["DATABASE_PATH"]

    # --- Login / logout ---
    @app.get("/login")
    def login():
        if not app.config.get("APP_PASSWORD") or session.get("authed"):
            return redirect(url_for("index"))
        return render_template("login.html", error=None)

    @app.post("/login")
    @rate_limit(10, 300)
    def login_post():
        password = request.form.get("password") or ""
        if password and password == app.config.get("APP_PASSWORD"):
            session["authed"] = True
            session.permanent = True
            return redirect(url_for("index"))
        return render_template("login.html", error="Contraseña incorrecta."), 401

    @app.get("/logout")
    def logout():
        session.pop("authed", None)
        return redirect(url_for("login"))

    # --- Página principal ---
    @app.get("/")
    @require_auth
    def index():
        return render_template("index.html")

    # --- Chat con Claude sobre el transcript (sin persistir) ---
    @app.post("/api/chat")
    @require_auth
    @rate_limit(30, 60)
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
                glossary=data["glossary"],
            )
        except Exception:
            return jsonify(
                {"error": "No se pudo contactar a la IA. Revisá la API key del servidor."}
            ), 502
        return jsonify({"reply": reply})

    # --- Chat con streaming (respuesta token por token, vía SSE) ---
    @app.post("/api/chat/stream")
    @require_auth
    @rate_limit(30, 60)
    def chat_stream():
        try:
            data = validate_chat_input(request.get_json(silent=True))
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400

        def generate():
            try:
                for chunk in anthropic_client.stream_ask(
                    transcript=data["transcript"],
                    question=data["question"],
                    history=data["messages"],
                    glossary=data["glossary"],
                ):
                    yield "data: " + json.dumps({"text": chunk}) + "\n\n"
                yield "event: done\ndata: {}\n\n"
            except Exception:
                yield "event: error\ndata: " + json.dumps(
                    {"error": "No se pudo contactar a la IA. Revisá la API key."}
                ) + "\n\n"

        return Response(generate(), mimetype="text/event-stream")

    # --- Resumen por plantilla (clase / reunión / entrevista) ---
    @app.post("/api/summary")
    @require_auth
    @rate_limit(30, 60)
    def summary():
        try:
            data = validate_summary_input(request.get_json(silent=True))
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        try:
            text = anthropic_client.generate_summary(
                data["transcript"], data["type"], glossary=data["glossary"]
            )
        except Exception:
            return jsonify({"error": "No se pudo generar el resumen. Revisá la API key."}), 502
        return jsonify({"summary": text})

    # --- Traducción del transcript ---
    @app.post("/api/translate")
    @require_auth
    @rate_limit(30, 60)
    def translate():
        try:
            data = validate_translate_input(request.get_json(silent=True))
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        try:
            text = anthropic_client.translate(
                data["transcript"], data["target"], glossary=data["glossary"]
            )
        except Exception:
            return jsonify({"error": "No se pudo traducir. Revisá la API key."}), 502
        return jsonify({"translation": text})

    # --- Mapa mental (Mermaid) ---
    @app.post("/api/mindmap")
    @require_auth
    @rate_limit(30, 60)
    def mindmap():
        try:
            data = validate_mindmap_input(request.get_json(silent=True))
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        try:
            code = anthropic_client.mindmap(data["transcript"], glossary=data["glossary"])
        except Exception:
            return jsonify({"error": "No se pudo generar el mapa mental. Revisá la API key."}), 502
        return jsonify({"mermaid": code})

    # --- Flashcards: generar con IA ---
    @app.post("/api/flashcards/generate")
    @require_auth
    @rate_limit(30, 60)
    def flashcards_generate():
        try:
            data = validate_flashcards_gen_input(request.get_json(silent=True))
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        try:
            cards = anthropic_client.generate_flashcards(
                data["transcript"], data["count"], glossary=data["glossary"]
            )
        except Exception:
            return jsonify({"error": "No se pudieron generar las tarjetas. Probá de nuevo."}), 502
        if not cards:
            return jsonify({"error": "La IA no devolvió tarjetas válidas. Probá de nuevo."}), 502
        return jsonify({"cards": cards})

    # --- Flashcards: guardar mazo ---
    @app.post("/api/flashcards")
    @require_auth
    def flashcards_save():
        try:
            data = validate_flashcards_save_input(request.get_json(silent=True))
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        saved = save_flashcards(db_path(), data["cards"])
        return jsonify({"saved": saved}), 201

    # --- Flashcards: las que toca repasar hoy ---
    @app.get("/api/flashcards/due")
    @require_auth
    def flashcards_due():
        today = date.today().isoformat()
        return jsonify(
            {
                "cards": list_due_flashcards(db_path(), today),
                "stats": flashcard_stats(db_path(), today),
            }
        )

    # --- Flashcards: calificar una tarjeta (SM-2) ---
    @app.post("/api/flashcards/<int:card_id>/grade")
    @require_auth
    def flashcards_grade(card_id):
        try:
            data = validate_grade_input(request.get_json(silent=True))
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        card = get_flashcard(db_path(), card_id)
        if card is None:
            return jsonify({"error": "Tarjeta no encontrada."}), 404
        nxt = sm2(data["quality"], card["repetitions"], card["easiness"], card["interval_days"])
        due = (date.today() + timedelta(days=nxt["interval_days"])).isoformat()
        update_flashcard_srs(
            db_path(),
            card_id,
            nxt["repetitions"],
            nxt["easiness"],
            nxt["interval_days"],
            due,
        )
        return jsonify({"ok": True, "due_date": due, "interval_days": nxt["interval_days"]})

    # --- Guardar una sesión en SQLite ---
    @app.post("/api/sessions")
    @require_auth
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
    @require_auth
    def get_sessions():
        return jsonify(list_sessions(db_path()))

    # --- Leer una sesión completa ---
    @app.get("/api/sessions/<int:session_id>")
    @require_auth
    def read_session(session_id):
        session = get_session(db_path(), session_id)
        if session is None:
            return jsonify({"error": "Sesión no encontrada."}), 404
        return jsonify(session)

    # --- Borrar una sesión ---
    @app.delete("/api/sessions/<int:session_id>")
    @require_auth
    def remove_session(session_id):
        if not delete_session(db_path(), session_id):
            return jsonify({"error": "Sesión no encontrada."}), 404
        return jsonify({"ok": True})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
