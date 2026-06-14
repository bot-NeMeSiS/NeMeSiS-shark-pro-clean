# CHATGPT CONTINUATION REPORT

## Estado actual

NeMeSiS SHARK PRO queda en version `V771_TELEGRAM_ACTIVITY_PRO_FORMAT_SCHEDULE_FINAL`.

La base anterior ya tenia Telegram manual/automatico, Render Cron, picks, live, calendario, resultados, highlights, Track Record, Data Marketplace, Automation Center y Madrid Time. V771 se centra solo en profesionalizar la actividad de Telegram sin rehacer modulos ni romper lo estable.

## Cambios principales

- Nuevo motor de planificacion Telegram: `engines/telegram_activity_engine.py`.
- Nuevo formateador premium de mensajes: `engines/telegram_message_formatter.py`.
- Integracion V771 dentro de `telegram_scheduler_delivery()`.
- Nuevos endpoints admin protegidos para actividad, schedule, preview y dedupe.
- Panel `/admin/telegram/command-center` ampliado con estado de actividad V771.
- Runner Render Cron con logs compactos y utiles.
- Variables nuevas en `.env.example` y `.env.render.clean`.
- Nuevo check: `tools/check_v771_telegram_activity_pro_format_schedule.py`.
- Reportes V771 generados.

## Estado Telegram

Telegram manual no se ha tocado. Telegram automatico sigue usando `/api/automation/telegram/tick` y el runner `tools/render_cron_telegram_tick.py`.

V771 anade actividad media-alta sin spam:

- resumen diario;
- mediodia;
- live;
- picks premium;
- resultados;
- highlights;
- recordatorios prepartido;
- cierre del dia.

El canal global sigue siendo destino valido. Privados vinculados siguen dependiendo de la logica existente de suscriptores y membresias.

No se envio Telegram real en local.

## Estado Render

La solucion sigue dependiendo de Render Cron. El Web Service por si solo no garantiza ejecucion continua sin trafico.

Cron recomendado: `*/10 * * * *`. Alternativa: `*/15 * * * *`.

## Riesgos y limites

- Si no hay datos reales de partidos, picks, resultados o highlights, V771 no envia relleno falso.
- Si faltan `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` o `AUTOMATION_SECRET`, no habra envio real.
- Los mensajes visibles nuevos evitan UTC y duplicados de hora, pero la app aun conserva texto legacy con mojibake en zonas antiguas fuera del alcance de V771.

## Siguiente paso recomendado

1. Configurar Render Cron con frecuencia 10 o 15 minutos.
2. Abrir `/admin/telegram/command-center`.
3. Revisar `/api/admin/telegram/message-preview`.
4. Confirmar que el canal recibe al menos un mensaje real cuando haya candidato.
5. Despues centrarse en pagos, diseno final, datos y venta.

