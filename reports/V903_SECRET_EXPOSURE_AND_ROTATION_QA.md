# V903 Secret Exposure And Rotation QA

## Estado
Se mantiene la politica V902B: ningun secreto real debe imprimirse en reportes, logs, runtime ni URLs seguras.

## Saneado
- `tools/render_cron_telegram_tick.py` muestra `secret=***hidden***&runner=render_cron`.
- Runtime muestra estados como `***configured***`, `***missing***` o booleanos.
- Reportes antiguos con ejemplos demasiado literales fueron saneados en V902B.

## Rotacion obligatoria recomendada
Si una URL real con `secret=` aparecio en chat, capturas o logs visibles, `AUTOMATION_SECRET` debe rotarse manualmente:
1. Cambiar `AUTOMATION_SECRET` en Render Web Service.
2. Cambiar `AUTOMATION_SECRET` en Render Cron Job al mismo valor nuevo.
3. No pegar el valor en GitHub, reportes, capturas ni chats.
4. Probar que endpoints sin secreto devuelven `403`.
5. Probar dry-run con el nuevo secreto desde entorno seguro.
6. Confirmar que el secreto viejo ya no funciona.

## No realizado
Codex no genero, no vio y no cambio secretos reales.
