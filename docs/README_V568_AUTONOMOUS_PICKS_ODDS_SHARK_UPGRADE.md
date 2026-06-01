# NeMeSiS SHARK PRO — V568 Autonomous Picks + Odds + SHARK Upgrade

## Objetivo
Fortalecer el valor principal de la app: recomendaciones automáticas y picks a partir de partidos próximos reales, cuotas cacheadas cuando existan y priorización de ligas importantes.

## Incluye
- Nueva ruta cliente `/auto-picks` y alias `/oportunidades`.
- Nuevo panel admin `/admin/autonomous-picks`.
- APIs:
  - `/api/v568/autonomous-picks-check`
  - `/api/autonomous-picks/status`
  - `/api/autonomous-picks/generate`
  - `/api/recommendations/auto`
  - `/api/admin/autonomous-picks/convert`
  - `/api/telegram/enqueue-auto-picks`
- Score SHARK por partido.
- Riesgo BAJO / MEDIO / ALTO.
- Confianza, value y stake sugerido.
- Priorización de ligas importantes.
- Uso de cuotas reales cacheadas si existen.
- Si no hay cuota, muestra “cuota pendiente”; no inventa cuotas.
- Integración visual en `/picks`.
- Conversión admin de recomendación en pick publicado.
- Mensaje preparado para Telegram con top oportunidades.

## Seguridad de datos
- No se inventan cuotas.
- No se inventan marcadores.
- No se marcan recomendaciones como picks publicados sin conversión/admin.
- Los partidos deben venir de calendario real, SportsDB, Odds o import legal.

## QA
- `app.py` compila OK.
- `compileall app.py engines` OK.
- ZIP limpio sin `.git`, `__pycache__`, DB local, logs ni ZIPs antiguos.
