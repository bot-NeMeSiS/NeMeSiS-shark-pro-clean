# V773 Render QA Checklist

1. Confirmar `/api/runtime-version` muestra `V773_DATA_MARKETPLACE_AUTOMATION_VIDEO_UX_QUALITY_POLISH`.
2. Entrar como admin y abrir:
   - `/admin/control-center`
   - `/admin/telegram/command-center`
   - `/admin/data-marketplace`
   - `/admin/automation-center`
   - `/admin/app-experience-quality`
3. Probar exportaciones:
   - `/api/admin/data-marketplace/export/closed-picks`
   - `/api/admin/data-marketplace/export/market-performance`
   - `/api/admin/data-marketplace/export/monthly-report?format=json`
4. Confirmar que ninguna exportación contiene emails, passwords, tokens, chat IDs ni datos personales.
5. Ejecutar Cron Telegram real o esperar al siguiente tick:
   - `python tools/render_cron_telegram_tick.py`
6. Revisar `/admin/automation-center` después del tick.
7. Confirmar Madrid Time y ausencia de UTC crudo en cliente.
8. Confirmar que el cliente no ve textos técnicos de admin.
