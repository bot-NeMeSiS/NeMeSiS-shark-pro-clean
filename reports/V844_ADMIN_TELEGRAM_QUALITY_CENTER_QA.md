# V844 Admin Telegram Quality Center QA

## Añadido al diagnóstico
	elegram_diagnostics() expone 844_quality con:
- policy: top_football_only_no_filler.
- allowed_preview.
- blocked_preview.
- last_no_filler.

## Objetivo
El admin puede ver por qué se envía o bloquea un candidato sin mostrar secretos ni enviar mensajes reales en local.

## Resultado
	ools/check_v844_admin_telegram_quality_center.py pasa correctamente.
