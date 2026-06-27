"""Capa de transcripción: habla con la API de Groq (Whisper). Free tier.

Es lo único que toca el servicio de transcripción. Si cambiás de proveedor,
tocás solo este archivo.
"""
import httpx

from config import Config

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


def transcribe(audio_bytes, filename, language=None):
    """Manda el audio a Groq/Whisper y devuelve el texto transcripto."""
    files = {"file": (filename, audio_bytes)}
    data = {"model": Config.GROQ_MODEL, "response_format": "json"}
    lang = language or Config.TRANSCRIBE_LANG
    if lang:
        data["language"] = lang
    headers = {"Authorization": f"Bearer {Config.GROQ_API_KEY}"}
    resp = httpx.post(GROQ_URL, headers=headers, data=data, files=files, timeout=120)
    resp.raise_for_status()
    return (resp.json().get("text") or "").strip()
