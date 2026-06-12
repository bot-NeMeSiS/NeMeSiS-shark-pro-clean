# TELEGRAM RELIABILITY AUDIT V727

- Version: `V742_TOP_APP_LIVE_DETAIL_TRACK_RECORD_MATCH_INTELLIGENCE_VIDEO_HIGHLIGHTS_FINAL`
- Estado: `MISSING_BOT_TOKEN`
- Severidad: `critical`
- Explicacion: Telegram no puede enviar porque falta TELEGRAM_BOT_TOKEN.
- Que hacer: Configurar TELEGRAM_BOT_TOKEN en Render y redeployar.

## Variables configuradas
- `auto_generate_picks`: no
- `auto_send_enabled`: no
- `auto_send_telegram_picks`: no
- `automation_secret_configured`: no
- `bot_token_configured`: no
- `bot_username_configured`: no
- `chat_id_configured`: no
- `daily_automation_enabled`: no
- `enable_telegram_auto`: no
- `public_base_url_configured`: no
- `scheduler_enabled`: no
- `telegram_enabled`: no
- `telegram_football_only`: si
- `telegram_sport_mode`: football_only

## Rutas Telegram encontradas
- `/admin/telegram`
- `/admin/telegram/command-center`
- `/admin/telegram/diagnostics`
- `/api/admin/telegram/dry-run`
- `/api/admin/telegram/preview-next`
- `/api/admin/telegram/status`
- `/api/admin/telegram/test-send`
- `/api/automation/telegram/tick`
- `/api/telegram/auto-posts`
- `/api/telegram/auto-run`
- `/api/telegram/diagnostics`
- `/api/telegram/enqueue-daily-matches`
- `/api/telegram/enqueue-daily-picks`
- `/api/telegram/link-status`
- `/api/telegram/logs`
- `/api/telegram/process-queue`
- `/api/telegram/queue`
- `/api/telegram/repair-automatic`
- `/api/telegram/scheduler-manager`
- `/api/telegram/scheduler-tick`
- `/api/telegram/send`
- `/api/telegram/send-test`
- `/api/telegram/settings`
- `/api/telegram/settings/update`
- `/api/telegram/status`
- `/api/telegram/triggers`
- `/api/v495/telegram-auto-run`
- `/telegram`
- `/telegram/desvincular`
- `/telegram/regenerar-codigo`
- `/telegram/webhook`

## Conteos
- `already_sent`: 0
- `candidate_picks`: 0
- `delivery_memory_total`: 0
- `destinations`: 0
- `discarded`: 0
- `duplicates`: 0
- `failed_today`: 0
- `finished_matches`: 0
- `football_candidates`: 0
- `global_channel`: 0
- `missing_odds`: 0
- `missing_selection`: 0
- `non_football_discarded`: 0
- `old_matches`: 0
- `pending_queue`: 0
- `premium_eligible`: 0
- `private_destinations`: 0
- `sent_last_hour`: 0
- `sent_today`: 0

## Razones de descarte
- Sin descartes registrados en la muestra.

## Limites y ventanas
- `daily_picks_end`: 20:30
- `daily_picks_start`: 13:00
- `daily_summary_end`: 12:30
- `daily_summary_start`: 09:30
- `max_auto_picks_per_day`: 4
- `max_odds`: 4.5
- `max_per_day`: 8
- `max_per_hour`: 1
- `min_odds`: 1.4
- `min_pick_score`: 75
- `quiet_end`: 09:30
- `quiet_hours_active`: True
- `quiet_start`: 00:30
- `sent_last_hour`: 0
- `sent_today`: 0

## Dry-run
- Enviaria: no
- Candidatos: 0
- Descartados: 0
- Preview disponible: no

## Nota
Este script no envia mensajes Telegram, no muestra secrets y no requiere trafico real.
