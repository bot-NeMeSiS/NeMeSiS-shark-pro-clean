# V889 Telegram Premium Picks Intelligence Delivery

Version objetivo: `V889_TELEGRAM_PREMIUM_PICKS_INTELLIGENCE_DELIVERY_FINAL`.

V889 convierte el envio de picks por Telegram en un flujo con puerta de calidad: si no hay partido real, seleccion clara y cuota real, no se envia. El objetivo comercial es que Telegram parezca un servicio premium, no un canal de relleno.

Cambios principales:
- Nuevo motor `engines/telegram_pick_quality_engine.py`.
- Nuevos formatos premium en `engines/telegram_message_formatter.py`.
- Nuevas APIs admin protegidas para candidatos, preview, dry-run y resumen de calidad.
- Integracion Sentinel/AutoPilot para vigilar filler, duplicados, picks sin cuota y dry-run inseguro.

Politica V889:
- Mejor no enviar nada que enviar un pick malo.
- No se inventan cuotas, picks, partidos, resultados ni escudos.
- Dry-run no envia Telegram real ni escribe cola.
- Telegram real queda reservado a Cron/admin con secretos correctos y autorizacion operativa.
