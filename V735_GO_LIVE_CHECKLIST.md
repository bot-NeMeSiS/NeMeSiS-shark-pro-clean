# V735 Go Live Checklist

Versión: `V735_GO_LIVE_PRODUCTION_TELEGRAM_DATA_CERTIFICATION`

## Qué valida esta versión

V735 no abre pagos reales ni envía Telegram de prueba automáticamente. Añade un centro de certificación para comprobar si la app puede pasar de beta interna a beta pública controlada.

## Pruebas obligatorias en Render

1. `/api/runtime-version` debe devolver V735.
2. `/api/health` debe responder 200.
3. `/admin/go-live` debe abrir con sesión admin.
4. `/admin/production-readiness` debe abrir con sesión admin.
5. `/admin/telegram/command-center` debe explicar el estado real de Telegram.
6. `/api/automation/telegram/tick` sin secret debe devolver 403.
7. `/api/automation/telegram/tick?secret=***` debe devolver 200 o diagnóstico claro.
8. `/api/automation/daily/run` sin secret debe devolver 403.
9. `/api/automation/daily/run?secret=***` debe devolver 200 o diagnóstico claro.
10. `/track-record` no debe inventar ROI: debe mostrar histórico real o estado de construcción.

## Regla de lanzamiento

- Si hay bloqueos críticos en Render, Telegram o Data Memory: no abrir a público grande.
- Si no hay bloqueos críticos y el score supera 75: beta controlada.
- Si supera 90 durante varios días con Telegram estable: pre-lanzamiento controlado.

## No tocar

- No tocar secrets reales.
- No cambiar `DB_PATH=/data/database.db`.
- No activar cobros automáticos sin prueba Stripe.
- No publicar ROI sin suficientes resultados reales.
