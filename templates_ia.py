"""Plantillas de resumen según el tipo de grabación.

Son solo instrucciones (prompts) que se le mandan a Claude junto con el
transcript. Texto plano legible, sin markdown, para mostrarse tal cual.
"""

SUMMARY_TYPES = ("clase", "reunion", "entrevista")

SUMMARY_TEMPLATES = {
    "clase": (
        "Resumí esta clase para un estudiante. Devolvé texto plano legible "
        "(sin markdown ni asteriscos), con estas secciones en MAYÚSCULA "
        "seguidas de dos puntos, y listas con guiones:\n"
        "TEMA PRINCIPAL:\n"
        "CONCEPTOS CLAVE:\n"
        "TAREAS Y FECHAS IMPORTANTES:\n"
        "PARA REPASAR:\n"
        "Si una sección no aplica, omitila."
    ),
    "reunion": (
        "Resumí esta reunión. Devolvé texto plano legible (sin markdown), con "
        "estas secciones en MAYÚSCULA y listas con guiones:\n"
        "OBJETIVO:\n"
        "PUNTOS TRATADOS:\n"
        "DECISIONES:\n"
        "ACCIÓN A SEGUIR (con responsable y fecha si se mencionan):\n"
        "Si una sección no aplica, omitila."
    ),
    "entrevista": (
        "Resumí esta entrevista. Devolvé texto plano legible (sin markdown), con "
        "estas secciones en MAYÚSCULA y listas con guiones:\n"
        "PARTICIPANTES Y ROLES:\n"
        "TEMAS:\n"
        "RESPUESTAS DESTACADAS:\n"
        "CONCLUSIONES:\n"
        "Si una sección no aplica, omitila."
    ),
}
