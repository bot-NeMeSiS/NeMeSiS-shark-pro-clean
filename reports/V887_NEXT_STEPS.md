# V887 Next Steps

## Acción inmediata

1. Revisar validaciones locales V887.
2. Subir V887 al repositorio correcto.
3. Hacer deploy manual en Render.
4. Ejecutar de nuevo `/api/runtime-version`.
5. Confirmar que Render muestra `V887_TELEGRAM_QUEUE_SKIPPED_RUNTIME_HOTFIX_FINAL`.
6. Ejecutar el Cron Telegram con `runner=render_cron`.
7. Confirmar que no vuelve a aparecer `name 'QUEUE_SKIPPED' is not defined`.

## No probado en V887 local

- Telegram real.
- Envío real a canal.
- Pagos reales.
- Deploy real Render.

## Si el error persiste tras deploy

Revisar:

- que Render está desplegando el repo correcto;
- que Render está en la rama correcta;
- que `app.py` desplegado importa `QUEUE_SKIPPED`;
- que `engines/telegram_delivery_engine.py` desplegado define `QUEUE_SKIPPED`;
- que no hay build cache sirviendo versión anterior;
- que `/api/runtime-version` muestra V887.

