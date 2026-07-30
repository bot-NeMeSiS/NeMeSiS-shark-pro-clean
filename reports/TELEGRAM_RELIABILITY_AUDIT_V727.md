# TELEGRAM RELIABILITY AUDIT V727

- Version: `V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL`
- Estado: `MISSING_BOT_TOKEN`
- Severidad: `critical`
- Explicacion: Telegram no puede enviar porque falta TELEGRAM_BOT_TOKEN.
- Que hacer: Configurar TELEGRAM_BOT_TOKEN en Render y redeployar.

## Variables configuradas
- `app_timezone_configured`: no
- `audit`: {'ok': False, 'telegram_bot_token_present': False, 'telegram_chat_id_present': False, 'telegram_bot_username_present': False, 'automation_secret_present': False, 'public_base_url': '', 'public_base_url_ok': False, 'timezone_ok': False, 'auto_flags_ok': False, 'auto': {'enabled': False, 'required_flags': {'ENABLE_TELEGRAM_AUTO': False, 'AUTO_SEND_TELEGRAM_PICKS': False, 'TELEGRAM_AUTO_SEND_ENABLED': False, 'ENABLE_TELEGRAM_AUTOMATION': False}, 'blocking_flags': ['ENABLE_TELEGRAM_AUTO', 'AUTO_SEND_TELEGRAM_PICKS', 'TELEGRAM_AUTO_SEND_ENABLED', 'ENABLE_TELEGRAM_AUTOMATION'], 'legacy_flags': {'TELEGRAM_ENABLED': False, 'RUN_DAILY_AUTOMATION': False, 'SCHEDULER_ENABLED': False, 'DAILY_AUTOMATION_ENABLED': False}}, 'web_service_required': {'AUTOMATION_SECRET': False, 'TELEGRAM_BOT_TOKEN': False, 'TELEGRAM_CHAT_ID': False, 'TELEGRAM_BOT_USERNAME': False, 'ENABLE_TELEGRAM_AUTO': False, 'AUTO_SEND_TELEGRAM_PICKS': True, 'TELEGRAM_AUTO_SEND_ENABLED': False, 'ENABLE_TELEGRAM_AUTOMATION': False, 'AUTO_GENERATE_PICKS': True, 'TZ': False, 'APP_TIMEZONE': False, 'PUBLIC_BASE_URL': False}, 'cron_required': {'PUBLIC_BASE_URL': False, 'AUTOMATION_SECRET': False}, 'missing': ['AUTOMATION_SECRET', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_BOT_USERNAME', 'ENABLE_TELEGRAM_AUTO', 'TELEGRAM_AUTO_SEND_ENABLED', 'ENABLE_TELEGRAM_AUTOMATION', 'TZ', 'APP_TIMEZONE', 'PUBLIC_BASE_URL'], 'warnings': ['PUBLIC_BASE_URL falta en el entorno.', 'Faltan flags oficiales de Telegram automático en true: ENABLE_TELEGRAM_AUTO, AUTO_SEND_TELEGRAM_PICKS, TELEGRAM_AUTO_SEND_ENABLED, ENABLE_TELEGRAM_AUTOMATION'], 'conflicts': [], 'masked': {'AUTOMATION_SECRET': '', 'TELEGRAM_BOT_TOKEN': '', 'TELEGRAM_CHAT_ID': ''}}
- `auto_generate_picks`: no
- `auto_send_enabled`: no
- `auto_send_telegram_picks`: no
- `automation_secret_configured`: no
- `blocking_flags`: ['ENABLE_TELEGRAM_AUTO', 'AUTO_SEND_TELEGRAM_PICKS', 'TELEGRAM_AUTO_SEND_ENABLED', 'ENABLE_TELEGRAM_AUTOMATION']
- `bot_token_configured`: no
- `bot_username_configured`: no
- `chat_id_configured`: no
- `daily_automation_enabled`: no
- `enable_telegram_auto`: no
- `enable_telegram_automation`: no
- `public_base_url_configured`: no
- `required_flags`: {'ENABLE_TELEGRAM_AUTO': False, 'AUTO_SEND_TELEGRAM_PICKS': False, 'TELEGRAM_AUTO_SEND_ENABLED': False, 'ENABLE_TELEGRAM_AUTOMATION': False}
- `scheduler_enabled`: no
- `telegram_auto_send_enabled`: no
- `telegram_enabled`: no
- `telegram_football_only`: si
- `telegram_sport_mode`: football_only
- `tz_configured`: no

## Rutas Telegram encontradas
- `/admin/telegram`
- `/admin/telegram-audit`
- `/admin/telegram/command-center`
- `/admin/telegram/diagnostics`
- `/admin/telegram/pro-preview`
- `/api/admin/company-intelligence/telegram`
- `/api/admin/telegram/activity-plan`
- `/api/admin/telegram/auto-candidates`
- `/api/admin/telegram/blocked-picks`
- `/api/admin/telegram/dedupe-status`
- `/api/admin/telegram/dry-run`
- `/api/admin/telegram/dry-run-premium-picks`
- `/api/admin/telegram/environment-audit`
- `/api/admin/telegram/message-preview`
- `/api/admin/telegram/pick-candidates`
- `/api/admin/telegram/pick-dry-run`
- `/api/admin/telegram/pick-preview`
- `/api/admin/telegram/pick-quality`
- `/api/admin/telegram/pick-quality-summary`
- `/api/admin/telegram/premium-preview`
- `/api/admin/telegram/preview-next`
- `/api/admin/telegram/pro-preview`
- `/api/admin/telegram/quality-status`
- `/api/admin/telegram/schedule-status`
- `/api/admin/telegram/schema`
- `/api/admin/telegram/status`
- `/api/admin/telegram/test-send`
- `/api/automation/telegram/tick`
- `/api/telegram/auto-posts`
- `/api/telegram/auto-run`
- `/api/telegram/diagnostics`
- `/api/telegram/enqueue-daily-matches`
- `/api/telegram/enqueue-daily-picks`
- `/api/telegram/enqueue-recommendations`
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
- `/telegram/regenerar-código`
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
- `quiet_hours_active`: False
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
