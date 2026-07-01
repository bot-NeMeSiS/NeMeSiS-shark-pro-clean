# V873 SHARK OpenAI config state QA

## Runtime real

Render V871 reporta `openai_configured=false`.

## Decisión

No se toca `OPENAI_API_KEY`, no se inventa configuración y no se expone ningún secreto.

## Corrección V873

- Runtime local añade:
  - `openai_state`;
  - `shark_ai_mode`;
  - `shark_ai_note`.
- `/shark` muestra `Modo seguro activo` cuando no hay OpenAI.
- `/admin/shark-ai` muestra `SHARK IA avanzada pendiente de configuración` cuando falta OpenAI.

## Comportamiento correcto

Si falta OpenAI:

- El cliente ve fallback seguro.
- Admin ve configuración pendiente.
- SHARK no promete IA avanzada real.
- SHARK no inventa datos, cuotas ni picks.
