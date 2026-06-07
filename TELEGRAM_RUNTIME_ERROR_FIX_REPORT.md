# Reparación Telegram runtime ERR-20260607-073500-E650

## Causa raíz probable

La ruta de usuario `/telegram` dependía de columnas de vinculación Telegram en `users`. El código actual trabajaba con `telegram_link_expires_at`, mientras que la incidencia y el contrato funcional esperaban también `telegram_link_expires`.

En una base persistente antigua de Render, esa diferencia puede provocar error runtime al generar o leer el código de vinculación si la columna esperada no existe o si el valor solo está en el alias antiguo.

## Corrección aplicada

- Añadida migración segura de columna `users.telegram_link_expires`.
- Sincronización bidireccional entre:
  - `telegram_link_expires_at`
  - `telegram_link_expires`
- Generación de código Telegram escribe en ambas columnas.
- Lectura de caducidad acepta ambas columnas.
- Vinculación por webhook limpia ambas columnas al completar.
- Regeneración de código limpia ambas columnas.
- `/admin/telegram/diagnostics` ahora responde 200 con diagnóstico JSON para admin, en lugar de redirigir.

## Validación

- `/telegram` como cliente: 200.
- `/api/telegram/link-status`: 200.
- `/telegram/webhook` con `/start CODIGO`: 200 y vincula usuario.
- `/telegram/webhook` con `/link CODIGO`: 200 y vincula usuario.
- `/admin/telegram`: 200.
- `/admin/telegram/diagnostics`: 200.
- DB legacy con tabla `users` antigua: migración OK, ruta `/telegram` 200.
- `compileall` OK.
- `observability_errors` en DB de prueba: 0.

