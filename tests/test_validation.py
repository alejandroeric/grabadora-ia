"""Tests de validación de datos de entrada."""
import pytest

from validation import (
    ValidationError,
    validate_chat_input,
    validate_session_input,
)


def test_valid_session_input_trims_strings():
    clean = validate_session_input({"title": "  Clase  ", "transcript": "  hola  "})
    assert clean["title"] == "Clase"
    assert clean["transcript"] == "hola"
    assert clean["messages"] == []


def test_session_requires_title():
    with pytest.raises(ValidationError):
        validate_session_input({"title": "  ", "transcript": "hola"})


def test_session_requires_transcript():
    with pytest.raises(ValidationError):
        validate_session_input({"title": "Clase", "transcript": "   "})


def test_session_rejects_invalid_message_role():
    with pytest.raises(ValidationError):
        validate_session_input(
            {"title": "C", "transcript": "t", "messages": [{"role": "bot", "content": "x"}]}
        )


def test_session_body_must_be_dict():
    with pytest.raises(ValidationError):
        validate_session_input("no soy un dict")


def test_valid_chat_input():
    clean = validate_chat_input({"transcript": "hola", "question": "  ¿qué dijo?  "})
    assert clean["question"] == "¿qué dijo?"
    assert clean["transcript"] == "hola"


def test_chat_requires_question():
    with pytest.raises(ValidationError):
        validate_chat_input({"transcript": "hola", "question": ""})


def test_chat_requires_transcript():
    with pytest.raises(ValidationError):
        validate_chat_input({"transcript": "", "question": "¿algo?"})
