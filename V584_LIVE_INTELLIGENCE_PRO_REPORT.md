# V584 - Live Intelligence Pro

## Objetivo

Mejorar la experiencia Live existente sin crear nuevas pantallas ni menús, manteniendo compatibilidad con TheSportsDB, The Odds API, SHARK, Render y SQLite.

## Cambios realizados

- Estados Live enriquecidos: En directo, Descanso, Finalizado, Próximo y Suspendido.
- Momentum SHARK más visible en directo y detalle de partido.
- Alertas SHARK Live persistibles para uso interno y futura salida a Telegram.
- Timeline Live conectado a eventos reales extraídos de payloads persistidos.
- Fallback editorial seguro cuando no hay eventos reales: estado del partido sin inventar goles, tarjetas ni minutos.
- Caché SQLite enriquecida en `live_matches`.
- Histórico de eventos Live en `live_event_history`.
- Reutilización del timeline histórico desde `/match/<id>`.
- Endpoint de verificación: `/api/v584/live-intelligence-check`.
- `/api/live/deep` ahora incluye resumen de caché Live.
- Corrección de botones existentes con query rota:
  - `/match-hublane=...` -> `/match-hub?lane=...`
  - `/calendariolane=...` -> `/calendario?lane=...`
  - `/sharkmatch=...` -> `/shark?match=...`

## Archivos modificados

- `app.py`
- `engines/live_engine.py`
- `templates/live.html`
- `templates/match_detail.html`
- `templates/live_depth.html`
- `templates/admin_live_depth.html`
- `templates/calendar.html`
- `templates/match_hub.html`
- `VERSION.txt`
- `V584_LIVE_INTELLIGENCE_PRO_REPORT.md`

## SQLite

Migraciones seguras añadidas:

- Columnas nuevas en `live_matches`:
  - `state_key`
  - `state_label`
  - `score`
  - `momentum_json`
  - `alerts_json`
  - `timeline_json`
  - `event_count`
  - `cache_status`

- Nueva tabla:
  - `live_event_history`

No se cambia `DB_PATH`; sigue usando `/data/database.db` por defecto.

## Compatibilidad

- TheSportsDB: mantiene uso de API permitida y payload persistido.
- The Odds API: no se toca el flujo de cuotas.
- SHARK: se reutilizan momentum y alertas existentes.
- Telegram: no se rompe cola ni envío; las alertas Live quedan preparadas en `auto_alerts`.
- Render: sin cambios de infraestructura.
- SQLite: migraciones con `ALTER TABLE` seguro y `CREATE TABLE IF NOT EXISTS`.

## QA

- `app.py` compila OK.
- `engines/` compila OK.
- `database_manager.py` compila OK.
- Revisión estática de enlaces Live corregida.
- No se pudo ejecutar test client de Flask en este entorno porque el Python disponible no tiene `flask` instalado.

## Pendiente recomendado

- Probar en Render o entorno local con dependencias instaladas:
  - `/live`
  - `/live-depth`
  - `/match-hub?lane=live`
  - `/api/live/deep`
  - `/api/v584/live-intelligence-check`
- Confirmar con datos reales TheSportsDB si llegan eventos tipo gol, tarjeta, penalti, VAR o sustitución.
