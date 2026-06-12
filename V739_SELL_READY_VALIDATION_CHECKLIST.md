# V739 — Checklist de venta controlada

## Antes de publicitar fuerte
1. Subir V739 a Render.
2. Abrir `/api/runtime-version` y confirmar `V739_SALE_READY_HOME_DATA_PRODUCTION_FIX`.
3. Abrir `/api/health`.
4. Entrar como admin y revisar:
   - `/admin/final-release`
   - `/admin/go-live`
   - `/admin/production-readiness`
   - `/admin/telegram/command-center`
   - `/admin/visual-experience`
5. Confirmar que el home no muestra ceros falsos.
6. Confirmar que `/calendar`, `/sports-hub`, `/live`, `/picks`, `/combis` cargan sin 500.
7. Confirmar horarios Madrid con un partido de hora conocida.
8. Confirmar Cron:
   - sin secret: 403
   - con secret: 200
9. Confirmar Telegram real:
   - status configurado
   - dry-run explica candidatos o motivo de bloqueo
   - test-send manual solo desde admin si procede
10. Confirmar persistencia:
   - `DB_PATH=/data/database.db`
   - usuarios y datos siguen tras redeploy

## Para vender sin estar tocando cada día
- Mantener Render con persistent disk.
- No borrar DB de `/data`.
- Mantener secrets configurados.
- Revisar Telegram Command Center al menos una vez al día al principio.
- Revisar Final Release Center antes de campañas fuertes.
- No activar Stripe real hasta probar webhook con evento real/sandbox.

## Estado recomendado
Si V739 pasa esos puntos durante varios días, el estado objetivo es:

**BETA COMERCIAL CONTROLADA LISTA PARA PUBLICITAR**

Para público masivo grande, queda pendiente confirmar pagos reales y track record con historial suficiente.
