# Contexto del proyecto

## Sobre el dueño

Eric Nofal. Principiante en programación pero aprendiendo a usar Claude Code de forma profesional. Habla español rioplatense (Argentina, "vos").

Su enfoque NO es escribir código línea por línea — es escribir prompts profesionales y entender el ecosistema. Cuando le expliques cosas, hacelo paso a paso, con ejemplos concretos y preguntas para verificar comprensión. Evitá info dumps.

## Rol esperado del asistente

Actuar como experto en desarrollo web con Python y Flask.

## Qué es la app

App web de **grabación con IA para tomar notas en la facultad**.

El usuario graba una clase desde el celular o la tablet, la app transcribe en tiempo real, y al terminar puede chatear con Claude sobre lo grabado.
Ejemplos de uso: *"¿qué tareas dijo el profesor?"* / *"resumime en 5 puntos"*.

## Diseño visual

El diseño ya está aprobado: `prototipo_grabadora.html`. Implementar siguiendo esa estética:
- Dark mode.
- Tailwind vía CDN.
- Gradientes indigo → purple → pink.

## Stack técnico (NO negociable)

- **Lenguaje/Backend:** Python 3.10+ con Flask.
- **Base de datos:** SQLite, con **WAL mode** y **foreign keys habilitados**.
- **Frontend:** HTML servido por Flask + Tailwind vía CDN + JavaScript vanilla (sin frameworks JS).
- **IA:** SOLO la API de Anthropic (Claude). Usar el modelo más económico disponible para mantener bajo el costo de API (hoy, la familia Haiku es la más barata).
- **Transcripción:** Web Speech API del navegador (gratis, sin APIs extra).
- **Deployment:** Render + GitHub. Incluir `Procfile` y `requirements.txt` listos para deploy desde el primer commit.
- **NO** usar Node, frameworks JS, ni servicios de transcripción pagos.
- Si se proponen cambios estructurales (split de archivos, build tools, dependencias nuevas, etc.), pedir confirmación del dueño primero.

## Alcance del MVP — EXACTAMENTE esto, nada más

1. Grabar desde el navegador con transcripción en tiempo real (Web Speech API).
2. Ver el transcript completo al terminar la grabación.
3. Chat con Claude sobre el transcript (Anthropic API).
4. El usuario elige: guardar la sesión en SQLite o descartarla.

## Fuera del MVP — NO implementar ahora (es V2)

Plantillas predefinidas, glosarios especializados, corte de silencios, mapas mentales, diarización, integraciones externas (Notion/Drive/Slack), traducción, timestamps indexados, extracción de entidades automática, action items automáticos.

## Tests (pytest obligatorio)

- Guardado y lectura de sesiones en SQLite.
- Integración con Anthropic API (mock aceptable en tests).
- Validación de datos de entrada.

## Orden de trabajo — INFRAESTRUCTURA antes que cualquier código

1. **Paso 1:** `git init` + estructura de carpetas.
2. **Paso 2:** `requirements.txt` + `Procfile` + `.env.example`.
3. **Paso 3:** recién ahí, implementación.

> Ubicación del proyecto (confirmada por el dueño): `C:\Users\proyectos\grabadora`.

## Reglas no negociables

### Seguridad
- Secrets (API key de Anthropic, credenciales, etc.) **NUNCA en código fuente** ni en el frontend. Van en variables de entorno del servidor.
- La key de Anthropic va en la variable de entorno `ANTHROPIC_API_KEY`, nunca hardcodeada.
- `.env` debe estar en `.gitignore` — nunca se commitea. Se versiona un `.env.example` sin valores reales.
- Sin secrets hardcodeados. Sin rutas hardcodeadas.

### Control de versiones (git)

*Regla #1 — Inicialización obligatoria:* si la carpeta del proyecto no tiene .git/, ANTES de cualquier modificación proponer git init + primer commit con el estado actual.

*Regla #2 — Commits descriptivos:* mensajes claros, en castellano, que expliquen el "qué" y el "por qué". Evitar mensajes vagos tipo "fix", "update", "cambios", "campeon".

*Regla #3 — No commitear sin pedirlo:* no hacer commits automáticos sin que el dueño los apruebe explícitamente (salvo el primer commit de inicialización, que es esperado).

*Regla #4 — Backup antes de cambios riesgosos:* antes de modificar lógica sensible o estructura de archivos, sugerir backup primero.

Identidad git ya configurada globalmente: Eric Nofal / alejoanton@hotmail.com.

## Workflow profesional esperado

1. *Plan antes de código*: para tareas no triviales, presentar plan primero. Esperar OK.
2. *Edit > Write*: preferir Edit a Write siempre que se pueda. Solo usar Write para archivos nuevos o reescrituras planeadas.
3. *Leer antes de modificar*: nunca tocar archivo sin haberlo leído antes.
4. *Verificar visualmente*: después de cambios significativos, recomendar abrir la app y confirmar que todo funciona.

## Restricciones generales (defaults)

- *No commitear a git* sin que el dueño lo pida explícitamente.
- *No instalar paquetes nuevos* sin avisar y justificar.
- *No borrar archivos* sin confirmar.
- *Si existen instrucciones contradictorias*, preguntar al dueño cuál usar.

## Estilo de comunicación esperado

- Español rioplatense ("vos", no "tú").
- Paso a paso, con ejemplos concretos y preguntas de verificación.
- Validar el "por qué" antes del "cómo" cuando es un concepto nuevo.
- Sin emojis salvo que el dueño los use primero o los pida.
- Sin info dumps. Una idea por turno.
