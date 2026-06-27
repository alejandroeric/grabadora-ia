"""Capa de IA: lo único que habla con la API de Anthropic (Claude).

Concentra todas las tareas de IA: chat, resumen por plantilla, traducción
y mapa mental. Cada función acepta un `client` inyectado para mockear en tests.
"""
from anthropic import Anthropic

from config import Config
from templates_ia import SUMMARY_TEMPLATES

BASE_SYSTEM = (
    "Sos un asistente que ayuda a estudiantes a entender la transcripción de una "
    "clase grabada. Respondé siempre en español rioplatense, de forma clara y concisa. "
    "Basate únicamente en el contenido de la transcripción; si algo no aparece ahí, "
    "decilo en vez de inventar."
)


def _system(glossary=None):
    """Arma el system prompt, sumando el glosario técnico si lo hay."""
    if glossary:
        return (
            BASE_SYSTEM
            + "\n\nGlosario de términos técnicos a respetar (usá la grafía correcta y "
            "corregí los términos mal transcriptos según este glosario):\n"
            + glossary
        )
    return BASE_SYSTEM


def _transcript_context(transcript):
    return (
        "Esta es la transcripción de la clase:\n\n"
        f"<transcripcion>\n{transcript}\n</transcripcion>"
    )


def _complete(messages, system, client=None, max_tokens=None):
    client = client or Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=Config.ANTHROPIC_MODEL,
        max_tokens=max_tokens or Config.MAX_TOKENS,
        system=system,
        messages=messages,
    )
    return response.content[0].text


def _strip_fences(text):
    """Quita las comillas triples (```) si Claude las devuelve igual."""
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def build_messages(transcript, history, question):
    """Arma la lista de mensajes para el chat: contexto, historial y pregunta."""
    messages = [
        {"role": "user", "content": _transcript_context(transcript)},
        {"role": "assistant", "content": "Listo, leí la transcripción. ¿Qué querés saber?"},
    ]
    for m in history or []:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": question})
    return messages


def ask(transcript, question, history=None, glossary=None, client=None):
    """Chat: le pregunta a Claude sobre la transcripción."""
    return _complete(build_messages(transcript, history, question), _system(glossary), client)


def generate_summary(transcript, template_key, glossary=None, client=None):
    """Resumen estructurado según la plantilla (clase / reunión / entrevista)."""
    instructions = SUMMARY_TEMPLATES[template_key]
    prompt = f"{_transcript_context(transcript)}\n\n{instructions}"
    return _complete(
        [{"role": "user", "content": prompt}], _system(glossary), client, max_tokens=1500
    )


def translate(transcript, target_lang, glossary=None, client=None):
    """Traduce el contenido de la transcripción al idioma pedido."""
    prompt = (
        f"{_transcript_context(transcript)}\n\n"
        f"Traducí el contenido de la transcripción a {target_lang}. "
        "Devolvé solo la traducción, sin notas ni comentarios."
    )
    return _complete(
        [{"role": "user", "content": prompt}], _system(glossary), client, max_tokens=2000
    )


def mindmap(transcript, glossary=None, client=None):
    """Genera un mapa mental de los conceptos en sintaxis Mermaid."""
    prompt = (
        f"{_transcript_context(transcript)}\n\n"
        "Generá un mapa mental de los conceptos principales en sintaxis Mermaid "
        "(diagrama tipo 'mindmap'). Reglas estrictas: devolvé SOLO el código Mermaid, "
        "sin explicaciones y sin comillas triples. Empezá con la palabra 'mindmap' en la "
        "primera línea. Usá un nodo raíz con el tema central y ramas con conceptos y "
        "subconceptos. Mantené los textos cortos y SIN paréntesis, comillas ni caracteres "
        "especiales en los nodos."
    )
    text = _complete(
        [{"role": "user", "content": prompt}], _system(glossary), client, max_tokens=1200
    )
    return _strip_fences(text)
