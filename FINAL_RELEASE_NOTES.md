# FINAL RELEASE NOTES - V700 Ultimate Launch Edition

## Versi?n

`V700_ULTIMATE_LAUNCH_EDITION`

## Cambios principales

- Release unificada en `APP_VERSION` y `VERSION.txt`.
- Arranque Render m?s seguro: health ultraligero, home ligera y scheduler sin bloqueo en import.
- `rows()` convertido en helper SQL puro.
- `initialize_once()` centraliza seed/migraci?n idempotente.
- Recuperaci?n de contrase?a cliente/admin con token seguro de 30 minutos.
- Observabilidad admin restaurada.
- APIs de observabilidad restauradas.
- Login, admin-login y registro aligerados.
- Telegram env sync verificado en c?digo y smoke local.
- Smoke tests p?blicos, cliente y admin sin errores 500.

## Compatibilidad

- Render: compatible.
- SQLite persistente `/data/database.db`: compatible.
- Telegram: compatible.
- Membres?as: sin cambios de comportamiento.
- SHARK: sin cambios destructivos.
- Backups: sin cambios destructivos.

## Nota de despliegue

Subir esta versi?n a GitHub deber?a disparar redeploy autom?tico en Render si el servicio est? conectado a la rama principal.
