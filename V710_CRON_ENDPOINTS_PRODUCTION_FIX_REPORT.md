# V710 CRON ENDPOINTS PRODUCTION FIX

## Objetivo
Cerrar el bloqueo de producción de Render Cron Jobs para Telegram automático sin rehacer la app y sin tocar lo que ya funcionaba.

## Cambios aplicados

- `APP_VERSION` actualizado a `V710_RENDER_CRON_AUTOMATION_FINAL`.
- `VERSION.txt` actualizado a `V710_RENDER_CRON_AUTOMATION_FINAL`.
- Endpoints Cron blindados:
  - `/api/automation/telegram/tick`
  - `/api/automation/daily/run`
- Validación estricta por `AUTOMATION_SECRET` para endpoints Cron:
  - Sin secret: `403` limpio.
  - Secret incorrecto: `403` limpio.
  - `AUTOMATION_SECRET` ausente en Render: `403` claro con `automation_secret_missing`.
  - Secret correcto: `200` aunque la automatización interna devuelva estado parcial/controlado.
- Los endpoints Cron ya no dependen de sesión admin.
- Se admite secret por:
  - `?secret=...`
  - header `X-Automation-Secret`
  - header `X-CRON-SECRET`
  - form/json `secret`
- Se añade ejecución segura para evitar que una excepción interna acabe en `internal_error`.
- Se registran marcas de última llamada en:
  - `last_cron_daily_call`
  - `last_cron_telegram_call`
  - y se mantienen claves legacy `cron_daily_run_last_call` / `cron_telegram_tick_last_call` por compatibilidad.
- `telegram_diagnostics()` ahora lee primero las claves nuevas y conserva fallback a las antiguas.
- Si los diagnósticos fallan, se devuelve diagnóstico mínimo seguro en vez de romper el endpoint Cron.

## Pruebas locales realizadas

Comando base de validación:

```bash
python3 -m compileall -q app.py engines services blueprints
```

Resultado:

```text
compile_ok
```

Smoke tests con `DB_PATH=/tmp/nemesis_v710.db` y `AUTOMATION_SECRET=abc`:

- `GET /api/automation/telegram/tick` -> `403` `automation_secret_required`
- `GET /api/automation/telegram/tick?secret=wrong` -> `403` `automation_secret_invalid`
- `GET /api/automation/telegram/tick?secret=abc` -> `200` con `cron: true` y versión V710
- `GET /api/automation/daily/run` -> `403` `automation_secret_required`
- `GET /api/automation/daily/run?secret=abc` -> `200` con `cron: true` y versión V710
- Sin `AUTOMATION_SECRET` configurado -> `403` `automation_secret_missing` claro

Nota: En local los envíos reales de Telegram pueden aparecer como `ok: false` por no tener red/API real o por token dummy, pero el endpoint responde `200` y no cae en `internal_error`. En Render, con tokens reales, deberá procesar la cola real.

## Siguiente paso en Render

1. Subir este ZIP a GitHub/Render.
2. Verificar `/version` o cualquier endpoint que muestre `version` y comprobar que aparece:
   `V710_RENDER_CRON_AUTOMATION_FINAL`.
3. Probar:
   - `/api/automation/telegram/tick` -> 403
   - `/api/automation/telegram/tick?secret=VALOR_REAL` -> 200
   - `/api/automation/daily/run` -> 403
   - `/api/automation/daily/run?secret=VALOR_REAL` -> 200
4. Crear los Cron Jobs reales en Render.

## Refuerzo extra aplicado en esta entrega

Además del bloqueo Cron, se corrigieron dos puntos que aparecieron al ejecutar la suite local:

- Se eliminó el fallback literal inseguro de `SECRET_KEY`; si no hay variable real en local, Flask usa un valor aleatorio temporal generado con `secrets.token_hex(32)`.
- Se recuperó el registro del blueprint de arquitectura V608:
  - `/admin/architecture`
  - `/api/architecture/summary`
  - `/api/v608/blueprint-migration-check`
- Se añadió `/api/security/summary` para diagnóstico admin de configuración sensible sin exponer secretos.

## Validación final adicional

```bash
pytest -q
```

Resultado:

```text
12 passed
```

```bash
python tools/smoke_check.py
```

Resultado:

```text
[OK] Compilación Python correcta
[OK] Templates referenciados disponibles
[OK] App importada correctamente
[OK] Sin rutas duplicadas exactas
[OK] Rutas críticas presentes
[OK] Smoke check finalizado
```
