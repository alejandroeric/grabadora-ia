"""Configuración de la app: lee todo desde variables de entorno.

Nada hardcodeado. Los secrets viven en el .env (que no se commitea).
"""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    # --- Anthropic (Claude) ---
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    # Modelo más económico por defecto (familia Haiku). Configurable por entorno.
    ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    MAX_TOKENS = int(os.environ.get("ANTHROPIC_MAX_TOKENS", "1024"))

    # --- Flask ---
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-inseguro-cambiar-en-produccion")

    # --- Seguridad ---
    # Si está definida, la app pide login con esta contraseña. Si está vacía,
    # queda abierta (cómodo para desarrollo local).
    APP_PASSWORD = os.environ.get("APP_PASSWORD", "")

    # --- Base de datos ---
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "grabadora.db")

    # --- Límites de validación de entrada ---
    MAX_TITLE_LEN = 200
    MAX_TRANSCRIPT_LEN = 200_000
    MAX_QUESTION_LEN = 4_000
    MAX_GLOSSARY_LEN = 5_000
