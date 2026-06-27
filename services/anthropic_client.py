"""Capa de IA: lo único que habla con la API de Anthropic (Claude).

Concentra todas las tareas de IA: chat, resumen por plantilla, traducción
y mapa mental. Cada función acepta un `client` inyectado para mockear en tests.
"""
import json

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


def stream_ask(transcript, question, history=None, glossary=None, client=None):
    """Igual que ask(), pero va devolviendo el texto en fragmentos (streaming)."""
    client = client or Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    with client.messages.stream(
        model=Config.ANTHROPIC_MODEL,
        max_tokens=Config.MAX_TOKENS,
        system=_system(glossary),
        messages=build_messages(transcript, history, question),
    ) as stream:
        for text in stream.text_stream:
            yield text


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


def generate_flashcards(transcript, count=8, glossary=None, client=None):
    """Genera tarjetas de estudio (pregunta/respuesta) a partir del transcript.

    Devuelve una lista de dicts {"question", "answer"}. Lanza excepción si la
    IA no devuelve un JSON parseable.
    """
    prompt = (
        f"{_transcript_context(transcript)}\n\n"
        f"Generá {count} tarjetas de estudio (flashcards) sobre los conceptos más "
        "importantes. Cada tarjeta debe tener una pregunta clara y una respuesta concisa. "
        "Devolvé SOLO un array JSON válido, sin texto adicional y sin comillas triples, "
        'con este formato exacto: [{"question": "...", "answer": "..."}]'
    )
    text = _strip_fences(
        _complete([{"role": "user", "content": prompt}], _system(glossary), client, max_tokens=2000)
    )
    data = json.loads(text)
    cards = []
    for item in data:
        if not isinstance(item, dict):
            continue
        q = (item.get("question") or "").strip()
        a = (item.get("answer") or "").strip()
        if q and a:
            cards.append({"question": q, "answer": a})
    return cards


def polish_transcript(transcript, glossary=None, client=None):
    """Devuelve la transcripción pulida (puntuación, mayúsculas, sin muletillas)."""
    prompt = (
        f"{_transcript_context(transcript)}\n\n"
        "Devolvé la MISMA transcripción pero pulida: corregí puntuación, mayúsculas y "
        "ortografía, sacá muletillas y repeticiones innecesarias ('eh', 'este', 'o sea'), y "
        "corregí términos técnicos mal transcriptos. NO resumas, NO cambies el contenido ni el "
        "idioma. Devolvé SOLO el texto pulido, sin comentarios ni comillas."
    )
    return _complete(
        [{"role": "user", "content": prompt}], _system(glossary), client, max_tokens=4000
    ).strip()


def extract_tasks(transcript, glossary=None, client=None):
    """Extrae tareas/fechas como lista de {'task', 'due'}."""
    prompt = (
        f"{_transcript_context(transcript)}\n\n"
        "Extraé las tareas, entregas y fechas importantes mencionadas. Devolvé SOLO un array "
        'JSON, sin texto extra ni comillas triples, con objetos {"task": "descripción corta", '
        '"due": "fecha o plazo si se menciona, si no cadena vacía"}. Si no hay tareas, devolvé [].'
    )
    text = _strip_fences(
        _complete([{"role": "user", "content": prompt}], _system(glossary), client, max_tokens=1500)
    )
    out = []
    for it in json.loads(text):
        if isinstance(it, dict) and (it.get("task") or "").strip():
            out.append({"task": it["task"].strip(), "due": (it.get("due") or "").strip()})
    return out


def generate_quiz(transcript, count=5, glossary=None, client=None):
    """Genera un cuestionario de opción múltiple."""
    prompt = (
        f"{_transcript_context(transcript)}\n\n"
        f"Generá un cuestionario de {count} preguntas de opción múltiple sobre los conceptos "
        "clave. Devolvé SOLO un array JSON, sin texto extra ni comillas triples, con objetos: "
        '{"question": "...", "options": ["a","b","c","d"], "correct": 0, "explanation": "..."}. '
        "'correct' es el índice (0-3) de la opción correcta."
    )
    text = _strip_fences(
        _complete([{"role": "user", "content": prompt}], _system(glossary), client, max_tokens=2500)
    )
    quiz = []
    for it in json.loads(text):
        if not isinstance(it, dict):
            continue
        q = (it.get("question") or "").strip()
        opts = it.get("options")
        if not q or not isinstance(opts, list) or len(opts) < 2:
            continue
        try:
            correct = int(it.get("correct", 0))
        except (TypeError, ValueError):
            correct = 0
        correct = max(0, min(len(opts) - 1, correct))
        quiz.append(
            {
                "question": q,
                "options": [str(o) for o in opts],
                "correct": correct,
                "explanation": (it.get("explanation") or "").strip(),
            }
        )
    return quiz


def comparison_table(transcript, glossary=None, client=None):
    """Arma un cuadro comparativo: {'title', 'headers', 'rows'}."""
    prompt = (
        f"{_transcript_context(transcript)}\n\n"
        "Armá un cuadro comparativo / sinóptico de los conceptos principales. Devolvé SOLO un "
        "objeto JSON, sin texto extra ni comillas triples: "
        '{"title": "título", "headers": ["Col1","Col2"], "rows": [["...","..."]]}. '
        "Elegí columnas que tengan sentido para comparar (ej: Concepto, Definición, Ejemplo)."
    )
    text = _strip_fences(
        _complete([{"role": "user", "content": prompt}], _system(glossary), client, max_tokens=2000)
    )
    data = json.loads(text)
    headers = [str(h) for h in (data.get("headers") or [])]
    rows = [[str(c) for c in r] for r in (data.get("rows") or []) if isinstance(r, list)]
    return {"title": (data.get("title") or "Cuadro comparativo").strip(), "headers": headers, "rows": rows}
