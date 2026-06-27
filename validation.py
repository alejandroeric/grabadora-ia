"""Validación de datos de entrada de la API.

Se separa de las rutas para poder testearla de forma aislada.
"""
from config import Config
from templates_ia import SUMMARY_TYPES


class ValidationError(ValueError):
    """Error de validación de datos de entrada (se traduce a HTTP 400)."""


def _require_dict(data):
    if not isinstance(data, dict):
        raise ValidationError("El cuerpo debe ser un objeto JSON.")
    return data


def _require_transcript(data):
    transcript = (data.get("transcript") or "").strip()
    if not transcript:
        raise ValidationError("Falta el transcript para darle contexto a la IA.")
    if len(transcript) > Config.MAX_TRANSCRIPT_LEN:
        raise ValidationError("El transcript es demasiado largo.")
    return transcript


def _clean_glossary(data):
    glossary = (data.get("glossary") or "").strip()
    if len(glossary) > Config.MAX_GLOSSARY_LEN:
        raise ValidationError("El glosario es demasiado largo.")
    return glossary


def _validate_messages(messages):
    if messages is None:
        return []
    if not isinstance(messages, list):
        raise ValidationError("El campo 'messages' debe ser una lista.")
    clean = []
    for m in messages:
        if not isinstance(m, dict):
            raise ValidationError("Cada mensaje debe ser un objeto.")
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if role not in ("user", "assistant"):
            raise ValidationError("Rol de mensaje inválido (debe ser user o assistant).")
        if not content:
            raise ValidationError("El contenido de un mensaje no puede estar vacío.")
        clean.append({"role": role, "content": content})
    return clean


def validate_session_input(data):
    """Valida el body para guardar una sesión. Devuelve datos limpios."""
    _require_dict(data)
    title = (data.get("title") or "").strip()
    transcript = (data.get("transcript") or "").strip()
    if not title:
        raise ValidationError("El título es obligatorio.")
    if len(title) > Config.MAX_TITLE_LEN:
        raise ValidationError("El título es demasiado largo.")
    if not transcript:
        raise ValidationError("El transcript no puede estar vacío.")
    if len(transcript) > Config.MAX_TRANSCRIPT_LEN:
        raise ValidationError("El transcript es demasiado largo.")
    return {
        "title": title,
        "transcript": transcript,
        "messages": _validate_messages(data.get("messages")),
    }


def validate_chat_input(data):
    """Valida el body para chatear con Claude. Devuelve datos limpios."""
    _require_dict(data)
    transcript = _require_transcript(data)
    question = (data.get("question") or "").strip()
    if not question:
        raise ValidationError("La pregunta no puede estar vacía.")
    if len(question) > Config.MAX_QUESTION_LEN:
        raise ValidationError("La pregunta es demasiado larga.")
    return {
        "transcript": transcript,
        "question": question,
        "messages": _validate_messages(data.get("messages")),
        "glossary": _clean_glossary(data),
    }


def validate_summary_input(data):
    """Valida el body para generar un resumen por plantilla."""
    _require_dict(data)
    transcript = _require_transcript(data)
    tipo = (data.get("type") or "clase").strip()
    if tipo not in SUMMARY_TYPES:
        raise ValidationError("Tipo de plantilla inválido.")
    return {"transcript": transcript, "type": tipo, "glossary": _clean_glossary(data)}


def validate_translate_input(data):
    """Valida el body para traducir el transcript."""
    _require_dict(data)
    transcript = _require_transcript(data)
    target = (data.get("target") or "").strip()
    if not target:
        raise ValidationError("Falta el idioma de destino.")
    if len(target) > 50:
        raise ValidationError("Idioma de destino inválido.")
    return {"transcript": transcript, "target": target, "glossary": _clean_glossary(data)}


def validate_mindmap_input(data):
    """Valida el body para generar el mapa mental."""
    _require_dict(data)
    transcript = _require_transcript(data)
    return {"transcript": transcript, "glossary": _clean_glossary(data)}


def validate_flashcards_gen_input(data):
    """Valida el body para generar flashcards con IA."""
    _require_dict(data)
    transcript = _require_transcript(data)
    try:
        count = int(data.get("count", 8))
    except (TypeError, ValueError):
        raise ValidationError("Cantidad de tarjetas inválida.")
    count = max(1, min(20, count))
    return {"transcript": transcript, "count": count, "glossary": _clean_glossary(data)}


def validate_flashcards_save_input(data):
    """Valida el body para guardar un mazo de flashcards."""
    _require_dict(data)
    cards = data.get("cards")
    if not isinstance(cards, list) or not cards:
        raise ValidationError("No hay tarjetas para guardar.")
    clean = []
    for c in cards:
        if not isinstance(c, dict):
            raise ValidationError("Tarjeta inválida.")
        question = (c.get("question") or "").strip()
        answer = (c.get("answer") or "").strip()
        if not question or not answer:
            raise ValidationError("Cada tarjeta necesita pregunta y respuesta.")
        clean.append({"question": question[:2000], "answer": answer[:4000]})
    return {"cards": clean}


def validate_grade_input(data):
    """Valida la calificación de una tarjeta (0-5)."""
    _require_dict(data)
    try:
        quality = int(data.get("quality"))
    except (TypeError, ValueError):
        raise ValidationError("Calificación inválida.")
    if quality < 0 or quality > 5:
        raise ValidationError("La calificación debe estar entre 0 y 5.")
    return {"quality": quality}


def validate_text_tool_input(data):
    """Valida herramientas que solo necesitan el transcript (pulir, tareas, cuadro)."""
    _require_dict(data)
    return {"transcript": _require_transcript(data), "glossary": _clean_glossary(data)}


def validate_quiz_input(data):
    """Valida la generación de cuestionario."""
    _require_dict(data)
    transcript = _require_transcript(data)
    try:
        count = int(data.get("count", 5))
    except (TypeError, ValueError):
        raise ValidationError("Cantidad de preguntas inválida.")
    count = max(1, min(15, count))
    return {"transcript": transcript, "count": count, "glossary": _clean_glossary(data)}
