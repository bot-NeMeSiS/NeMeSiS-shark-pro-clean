# V717 Production Polish Commercial Launch Upgrade

## Objetivo

Pulir NeMeSiS SHARK PRO para acercarlo a lanzamiento comercial sin rehacer la app ni romper Render, Telegram automático, Cron Jobs, SQLite persistente, seguridad V715/V716, login, admin, cliente, membresías, combis hasta 15 ni `DB_PATH=/data/database.db`.

## Problemas encontrados

- Los endpoints Cron funcionaban, pero devolvían JSON demasiado largo con diagnósticos y objetos internos.
- El detalle largo de ejecución no estaba separado claramente entre respuesta pública Cron y panel admin.
- Faltaban rutas legales básicas en inglés/esquema comercial: `/privacy`, `/terms`, `/contact`, `/responsible-gaming`.
- En la primera prueba V717, la nueva plantilla legal falló por usar `page.items`, que Jinja interpretó como método de diccionario. Corregido con `page["items"]`.
- El mensaje diario Telegram incluía versión técnica, poco útil para cliente/canal.
- El panel admin Telegram podía mostrar métricas, pero faltaba un bloque más claro de variables configuradas sin exponer valores.

## Mejoras aplicadas

### Seguridad producción y secrets

- No se añadió ningún secret real al código.
- Los endpoints Cron ya no devuelven diagnósticos largos por defecto.
- Se mantienen estados seguros:
  - configured true/false,
  - token/canal presentes sí/no,
  - secret configurado sí/no,
  - API keys configuradas sí/no.
- El detalle completo de ejecución Cron se guarda en `automation_state` para vistas admin.

### JSON Cron compacto

Se compactaron:

- `/api/automation/telegram/tick`
- `/api/automation/daily/run`

Ahora devuelven solo campos profesionales:

- `ok`
- `endpoint`
- `version`
- `status`
- `cron`
- contadores principales
- `state_saved`
- timestamps

No devuelven:

- `diagnostics`
- `state_save_results`
- objetos largos `result`
- payloads completos
- errores internos largos
- tokens
- chat IDs completos
- secrets

### Admin diagnostics

`/admin/telegram/diagnostics` mantiene detalle largo protegido.

Añadido bloque admin para:

- último Telegram Tick,
- último Daily Run,
- estado del token bot,
- estado del canal,
- estado de `AUTOMATION_SECRET`,
- estado de The Odds API / TheSportsDB,
- candidatos de auto picks,
- picks enviables,
- descartes por falta de cuota,
- total descartado,
- motivos de descarte.

### Telegram premium

- El mensaje diario ya no muestra versión técnica.
- El formato de picks Telegram es más corto:
  - Pick SHARK Premium,
  - competición,
  - hora España,
  - partido,
  - pick,
  - mercado,
  - cuota,
  - stake /10,
  - confianza,
  - riesgo,
  - motivo,
  - precaución.
- Se limita el bloque a 3 picks por mensaje para evitar saturación.
- Se mantiene el filtro que impide enviar picks antiguos, sin cuota real o no cerrados.

### Picks y combis

- Se conserva la separación V716:
  - Picks premium.
  - En estudio por SHARK.
- Se conserva validación comercial:
  - cuota real,
  - selección clara,
  - partido no antiguo,
  - sin `None/null/undefined`,
  - sin “esperar cuota”.
- Combis hasta 15 siguen funcionando con selector segura/media/larga y filtro de picks válidos.

### SHARK AI

- Se conserva SHARK más útil de V716.
- Botones rápidos incluyen:
  - Pick de hoy,
  - Mejores picks,
  - Combi segura,
  - Combi 15,
  - Directo,
  - Favoritos,
  - Oportunidades,
  - Riesgo,
  - Qué partido ver,
  - Explicar apuesta,
  - Resumen del día,
  - Telegram.

### Escudos e identidad

Se añadieron helpers centrales seguros:

- `safe_logo_url()`
- `fallback_team_badge()`
- `get_team_identity()`
- `get_team_logo()`

Estos envuelven el sistema existente `resolve_team()` y mantienen fallback profesional con iniciales/crest propio.

### Legal básico y confianza

Añadidas rutas:

- `/responsible-gaming`
- `/privacy`
- `/terms`
- `/contact`

Añadida plantilla:

- `templates/legal_basic.html`

Añadido footer global:

- Juego responsable
- Privacidad
- Términos
- Contacto

### Cliente

- Home pública no muestra versión técnica.
- Footer legal visible.
- No se han añadido textos técnicos al cliente.

## Archivos modificados

- `app.py`
- `VERSION.txt`
- `engines/telegram_delivery_engine.py`
- `templates/base.html`
- `templates/admin_telegram.html`
- `templates/legal_basic.html`
- `static/app.css`
- `tests/test_v716_release_validation.py`
- `tests/test_app_imports.py`
- `tools/smoke_check.py`
- `V717_PRODUCTION_POLISH_COMMERCIAL_LAUNCH_UPGRADE_REPORT.md`

## Validación ejecutada

- `python -m py_compile app.py engines/telegram_delivery_engine.py tools/validate_release.py`: OK
- `python -m compileall -q app.py engines database_manager.py services tools tests`: OK
- `python tools/smoke_check.py`: OK
- `python tools/validate_release.py`: OK hasta pytest; se detiene indicando que pytest no está instalado.
- `python -m pytest -q`: no ejecutable en este entorno porque `pytest` no está instalado.

Además, `tools/smoke_check.py` y el test de compilación se ajustaron para compilar código en memoria y no depender de escribir archivos `.pyc`, evitando bloqueos temporales de OneDrive/Windows sobre `__pycache__`.

`requirements.txt` sí incluye `pytest==8.3.4`. En un entorno con red:

```bash
pip install -r requirements.txt
pytest -q
```

## Smoke manual

Con Flask test client y DB temporal:

- `/`: 200
- `/login`: 200
- `/cliente-login`: 200
- `/admin-login`: 200
- `/registro`: 200
- `/sports-hub`: 200
- `/live`: 200
- `/calendar`: 200
- `/picks`: 200
- `/combis`: 200
- `/telegram`: 302 sin sesión, 200 con cliente
- `/shark`: 200
- `/favorites`: 302 sin sesión, 200 con cliente
- `/perfil`: 302 sin sesión, 200 con cliente
- `/membership`: 200
- `/responsible-gaming`: 200
- `/privacy`: 200
- `/terms`: 200
- `/contact`: 200
- `/api/runtime-version`: 200 y devuelve `V717_PRODUCTION_POLISH_COMMERCIAL_LAUNCH_UPGRADE`
- `/admin/telegram/diagnostics`: 200 con sesión admin
- `/admin/automation`: 200 con sesión admin

## Cron

- `/api/automation/telegram/tick` sin secret: 403
- `/api/automation/telegram/tick?secret=...`: 200
- `/api/automation/daily/run` sin secret: 403
- `/api/automation/daily/run?secret=...`: 200

JSON Cron confirmado compacto:

- Telegram Tick devuelve campos como `processed`, `sent`, `failed`, `skipped`.
- Daily Run devuelve campos como `matches_synced`, `picks_generated`, `picks_sent`, `backups_created`.
- No devuelve `diagnostics`, `result` ni `state_save_results`.

## Endpoints técnicos protegidos

Sin admin ni secret:

- `/api/diagnostics`: 403
- `/api/cache/status`: 403
- `/api/telegram/auto-run`: 403
- `/api/scheduler/status`: 403
- `/api/matches/diagnostics`: 403

## Pasos para rotar AUTOMATION_SECRET en Render

1. Abrir Render Dashboard.
2. Ir al Web Service de NeMeSiS SHARK PRO.
3. Entrar en Environment.
4. Cambiar `AUTOMATION_SECRET` por un valor nuevo:
   - largo,
   - privado,
   - sin espacios,
   - preferiblemente sin caracteres problemáticos para URL.
5. Guardar y redeployar si Render lo solicita.
6. Abrir cada Cron Job de Render.
7. Sustituir el valor antiguo en:
   - `/api/automation/telegram/tick?secret=NUEVO_VALOR`
   - `/api/automation/daily/run?secret=NUEVO_VALOR`
8. No guardar el secret en código, capturas, informes ni chats.
9. Probar:
   - sin secret debe dar 403,
   - con secret nuevo debe dar 200.

## Cómo probar en Render

1. Desplegar el ZIP V717.
2. Abrir `/api/runtime-version`.
3. Confirmar versión V717.
4. Probar `/`, `/sports-hub`, `/picks`, `/combis`, `/telegram`, `/shark`.
5. Probar Cron sin secret: 403.
6. Probar Cron con secret: 200 y JSON compacto.
7. Entrar como admin y abrir `/admin/telegram/diagnostics` para ver detalle largo.

## Pendiente real

- Verificar Telegram real en producción con bot/canal activos.
- Verificar volumen real de picks/cuotas según APIs conectadas.
- Verificar escudos reales según TheSportsDB/API disponible.
- Ejecutar `pytest -q` en entorno con pytest instalado.
