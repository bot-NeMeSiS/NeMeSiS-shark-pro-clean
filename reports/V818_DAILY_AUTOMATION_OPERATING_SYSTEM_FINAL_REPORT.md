# V818 Daily Automation Operating System Final

V818 crea `engines/daily_automation_engine.py` como coordinador central con hora Madrid, dedupe por fecha/job y memoria SQLite.

Jobs diarios:

- 00:10 `daily_close_previous_day`
- 02:30 `daily_data_backup_maintenance`
- 07:00 `morning_fixtures_sync`
- 09:00 `morning_odds_and_pick_candidates`
- 11:30 `telegram_daily_top_agenda`
- Cada tick `match_lifecycle_reconciler`, `live_tracker_smart_sync`, alertas Telegram controladas, resultados y health
- 22:45 `daily_evening_recap`

Endpoint Render:

`/api/automation/master-tick?secret=AUTOMATION_SECRET`

Seguridad:

- 403 sin secret.
- Idempotencia con `automation_dedupe`.
- Tablas nuevas compatibles con DB antigua.
- No inventa resultados, minutos, picks ni ROI.
- Errores tecnicos solo admin/panel.
