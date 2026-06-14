# Checklist Render V781

Después de desplegar V781:

1. Abrir `/api/runtime-version` y confirmar `V781_FULL_APP_AUDIT_STABILITY_MADRID_TIME_CLEANUP`.
2. Abrir `/app`, `/calendar?lane=today`, `/live`, `/picks`, `/track-record`, `/menu`, `/mi-cuenta`.
3. Probar `/live?refresh=1` y `/api/live/diagnostics?refresh=1` con sesión admin.
4. Confirmar escudos/fallbacks en calendario/directo/picks/detalle.
5. Confirmar que las horas visibles aparecen en formato Madrid, no UTC crudo.
6. Confirmar que Telegram Command Center carga y que el Cron sigue protegido.
7. Confirmar que no hay 500 en cliente ni admin.
