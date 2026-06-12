# V729 Security Audit

Versión: `V729_SECURITY_STABILITY_VISUAL_QA_FOUNDATION`

## Cambios aplicados

### SECRET_KEY estable

- `app.secret_key` ahora usa `secure_secret_key()` desde `engines/security_engine.py`.
- Se elimina el fallback peligroso de sesión aleatoria en producción (`secrets.token_hex(32)` en el arranque Flask).
- En Render/producción, si falta `SECRET_KEY` o `FLASK_SECRET_KEY`, la app debe fallar de forma clara en vez de invalidar sesiones silenciosamente.
- `.env.example` documenta `SECRET_KEY` como variable obligatoria.

### CSRF

- Se activa protección CSRF para métodos `POST`, `PUT`, `PATCH` y `DELETE` no exentos.
- Se añade token CSRF a `templates/base.html` como meta tag.
- Se inyecta automáticamente `<input type="hidden" name="csrf_token">` en formularios `POST` renderizados como HTML.
- Las peticiones JSON del widget SHARK y favoritos envían `X-CSRF-Token`.
- Se mantienen exentos los endpoints de Cron y webhook que no pueden depender de sesión HTML:
  - `/api/automation/telegram/tick`
  - `/api/automation/daily/run`
  - `/telegram/webhook`

### Rate limiting

- Se aplica limitación de intentos a flujos sensibles:
  - login cliente
  - login admin
  - registro
  - recuperación de contraseña
  - cambio de contraseña
  - test controlado de Telegram admin
- Los bloqueos quedan registrados en `security_events`.
- Los intentos correctos/fallidos de login y registro se registran como eventos de seguridad.

### Cabeceras de seguridad

Se añaden cabeceras básicas:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

## Validación estática

`tools/check_v729_security.py` verifica:

- versión V729 declarada
- `secure_secret_key()` en uso
- ausencia de fallback aleatorio de secret key en el arranque Flask
- CSRF importado y aplicado
- meta CSRF en `base.html`
- rate limiting presente
- eventos de login/registro registrados
- cabeceras de seguridad presentes
- 0 HTML duplicados en la raíz

Resultado local: OK.

## Qué no se tocó

- No se tocaron secrets reales.
- No se cambió `DB_PATH=/data/database.db`.
- No se cambió Render real.
- No se cambió Telegram real.
- No se rompió Madrid Time V728.
- No se migró `app.py` completo a blueprints para evitar riesgo alto en esta versión.
