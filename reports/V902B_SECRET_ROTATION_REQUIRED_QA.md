# V902B Secret Rotation Required QA

## Motivo
Se detectó una situación operativa donde una URL de Cron con parámetro `secret` pudo haber quedado expuesta. Aunque el código no imprime secretos completos tras V902B, cualquier secreto que haya aparecido fuera de Render debe rotarse.

## Regla V902B
- No se imprime el secreto completo.
- No se imprime el final del secreto.
- URLs seguras muestran `secret=***hidden***&runner=render_cron`.
- Runtime solo muestra estados booleanos o placeholders seguros.

## Pasos de rotación
1. Abrir Render Web Service `bot-apuestas-crgf`.
2. Cambiar `AUTOMATION_SECRET` por un valor nuevo y fuerte.
3. Abrir el Cron Job correspondiente.
4. Cambiar `AUTOMATION_SECRET` por el mismo valor nuevo.
5. No pegar el valor en GitHub, reportes, capturas ni chats.
6. Ejecutar un dry-run protegido si procede.
7. Confirmar que endpoints sin secreto devuelven 403.

## No realizado
No se rotó ningún secreto desde Codex. Requiere acción manual del propietario en Render.
