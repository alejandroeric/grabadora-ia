"""Validación de datos de entrada de la API.

Se separa de las rutas para poder testearla de forma aislada.
"""
from config import Config


class ValidationError(ValueError):
    """Error de validación de datos de entrada (se traduce a HTTP 400)."""


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
    if not isinstance(data, dict):
        raise ValidationError("El cuerpo debe ser un objeto JSON.")
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
    if not isinstance(data, dict):
        raise ValidationError("El cuerpo debe ser un objeto JSON.")
    transcript = (data.get("transcript") or "").strip()
    question = (data.get("question") or "").strip()
    if not transcript:
        raise ValidationError("Falta el transcript para darle contexto a la IA.")
    if not question:
        raise ValidationError("La pregunta no puede estar vacía.")
    if len(question) > Config.MAX_QUESTION_LEN:
        raise ValidationError("La pregunta es demasiado larga.")
    return {
        "transcript": transcript,
        "question": question,
        "messages": _validate_messages(data.get("messages")),
    }
