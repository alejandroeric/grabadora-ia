"""Capa de IA: lo único que habla con la API de Anthropic (Claude).

Si algún día cambiás de modelo o de proveedor, tocás solo este archivo.
La función `ask` acepta un `client` inyectado para poder mockearlo en tests.
"""
from anthropic import Anthropic

from config import Config

SYSTEM_PROMPT = (
    "Sos un asistente que ayuda a estudiantes a entender la transcripción de una "
    "clase grabada. Respondé siempre en español rioplatense, de forma clara y concisa. "
    "Basate únicamente en el contenido de la transcripción; si algo no aparece ahí, "
    "decilo en vez de inventar."
)


def build_messages(transcript, history, question):
    """Arma la lista de mensajes para la API de Anthropic.

    Mete la transcripción como contexto inicial, después el historial del
    chat y, por último, la nueva pregunta del usuario.
    """
    context = (
        "Esta es la transcripción de la clase:\n\n"
        f"<transcripcion>\n{transcript}\n</transcripcion>"
    )
    messages = [
        {"role": "user", "content": context},
        {"role": "assistant", "content": "Listo, leí la transcripción. ¿Qué querés saber?"},
    ]
    for m in history or []:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": question})
    return messages


def ask(transcript, question, history=None, client=None):
    """Le pregunta a Claude sobre la transcripción y devuelve el texto de respuesta."""
    client = client or Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=Config.ANTHROPIC_MODEL,
        max_tokens=Config.MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=build_messages(transcript, history, question),
    )
    return response.content[0].text
