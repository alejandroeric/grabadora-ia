"""Repaso espaciado: algoritmo SM-2 (el clásico de SuperMemo/Anki).

Recibe la calidad de la respuesta (0-5) y el estado actual de la tarjeta,
y devuelve el nuevo estado (repeticiones, facilidad e intervalo en días).
"""

DEFAULT_EASINESS = 2.5
MIN_EASINESS = 1.3


def sm2(quality, repetitions, easiness, interval_days):
    """Calcula el próximo estado de una tarjeta según SM-2.

    quality: 0-5 (0-2 = fallaste, 3-5 = la sabías con distinta soltura).
    """
    quality = max(0, min(5, int(quality)))

    if quality < 3:
        repetitions = 0
        interval_days = 1
    else:
        if repetitions == 0:
            interval_days = 1
        elif repetitions == 1:
            interval_days = 6
        else:
            interval_days = round(interval_days * easiness)
        repetitions += 1

    easiness = easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if easiness < MIN_EASINESS:
        easiness = MIN_EASINESS

    return {
        "repetitions": repetitions,
        "easiness": round(easiness, 4),
        "interval_days": int(interval_days),
    }
