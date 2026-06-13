# V766 Calendar Results Highlights Order Automation

## Objetivo
Ordenar el calendario y los resultados como una app vendible: sin pestaña Andalucía visible cuando no aporta partidos, con resultados claros, directos separados, próximos con hora Madrid, y resúmenes/highlights externos cuando TheSportsDB los proporcione.

## Cambios principales
- Retirada la pestaña cliente de Andalucía en calendario y directo.
- Añadida pestaña Resultados en calendario.
- Añadidas rutas cliente `/highlights`, `/resumenes` y `/resumenes-partidos`.
- Añadida API `/api/client/highlights`.
- Añadido endpoint protegido `/api/automation/highlights/sync` para sincronización diaria con `AUTOMATION_SECRET`.
- Añadido endpoint admin `/api/admin/highlights/sync` para sincronización manual.
- Integrado `sportsdb_highlights_engine.py` en pantallas cliente.
- En calendario/directo/detalle se muestra si hay resumen disponible o si está pendiente.
- Añadida estructura visual V766 para resultados, resúmenes, directos y próximos.

## Política legal y técnica
NeMeSiS no descarga ni rehostea vídeos. Solo guarda metadatos y enlaces externos aportados por API permitida. Si YouTube o la fuente externa bloquea un vídeo, la app lo mantiene como enlace externo o pendiente.

## No tocado
- Telegram automático.
- Render Cron de Telegram.
- `tools/render_cron_telegram_tick.py`.
- `/api/automation/telegram/tick`.
- `AUTOMATION_SECRET`.
- `DB_PATH`.
- Usuarios, sesiones, membresías y pagos reales.
- Madrid Time.

## Validación esperada en Render
- Configurar `THESPORTSDB_API_KEY` o `THESPORTSDB_KEY`.
- Ejecutar `/api/automation/highlights/sync?secret=AUTOMATION_SECRET&force=1`.
- Revisar `/highlights` y `/calendar?lane=results`.
