# NeMeSiS SHARK PRO — V713 COMBIS 15 + SHARK AI FINAL

Versión centrada en dos mejoras de producto cliente sin tocar el Cron/Telegram ya funcional:

- Combinadas ampliadas de 2 a 15 partidos.
- SHARK IA revisado para que los botones respondan con datos reales y texto útil, no frases genéricas.

## Cambios principales

- `APP_VERSION` y `VERSION.txt` actualizados a `V713_COMBIS15_SHARK_AI_FINAL`.
- Nuevo límite comercial `COMBI_MAX_LEGS = 15`.
- `/combis?partidos=15` disponible.
- Tabs visuales de combis de 2 a 15.
- Constructor de base de combis ampliado hasta 15 partidos reales.
- API `/api/combis/build` permite hasta 15 selecciones cuando hay picks suficientes.
- Widget SHARK IA mejorado:
  - Pick de hoy con cuota, stake, confianza y riesgo.
  - Favoritos con partidos reales cruzados.
  - Combinada responsable hasta 15 partidos.
  - Directo con marcador/minuto cuando exista.
  - Oportunidades SHARK con value/riesgo.
- Respuestas SHARK con saltos de línea y mayor claridad.
- Añadido `/version` público para verificar despliegue en Render.

## Validación

- `python -m compileall -q .` OK.
- `pytest -q` OK, 12 tests passed.
- `python tools/smoke_check.py` OK con los 2 warnings legacy ya conocidos.

## Nota responsable

SHARK permite estructuras hasta 15, pero avisa de que las combinadas largas son de riesgo alto. Para combinadas seguras prioriza 2-4 selecciones y no inventa picks si faltan cuotas o datos suficientes.
