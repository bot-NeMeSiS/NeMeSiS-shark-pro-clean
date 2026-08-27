# NEMESIS X PRODUCTION SCHEDULER CERTIFICATION

Estado: READY_FOR_PRODUCTION_SCHEDULER_APPROVAL_LOCAL.
Fecha Madrid: 2026-08-27.

## Decision arquitectonica

No se debe crear un Render Cron que ejecute directamente:

```text
python tools/run_continuous_evolution_scheduler.py --trigger SCHEDULED_PRODUCTION
```

Root cause: Render Cron no comparte el persistent disk del Web Service. Continuous Evolution necesita memoria persistente para snapshots, Product Memory, Founder Brief y Prepared for Codex.

## Arquitectura certificada localmente

```text
RENDER CRON
-> tools/render_cron_continuous_evolution_tick.py
-> HTTPS POST /api/automation/continuous-evolution/tick
-> Web Service Nemesis
-> Continuous Evolution safe runner
-> /data/continuous_evolution_os
```

El Cron queda stateless. La persistencia vive en el Web Service.

## Reused automation infrastructure

- `AUTOMATION_SECRET` existente.
- `automation_header_secret_status()`.
- `automation_header_json_forbidden()`.
- Rate limiting global de seguridad.
- CSRF exemption existente para endpoints `/api/automation` protegidos.
- Madrid Time del motor Continuous Evolution.
- Scheduler idempotente existente.
- Lock `scheduler.lock` existente.
- Estados `PASS`, `PARTIAL`, `SKIPPED_NOT_DUE`, `SKIPPED_ALREADY_RUNNING`, `SKIPPED_PAUSED`.
- Respuestas JSON sanitizadas.

## Nuevo endpoint

```text
POST /api/automation/continuous-evolution/tick
```

No acepta GET mutante.
No acepta secret por query.
No acepta task arbitrario.
No acepta force.
No acepta shell input.
No acepta paths arbitrarios.

## Safe Mode

El endpoint exige:

```text
CONTINUOUS_EVOLUTION_SAFE_MODE=1
```

Si falta: `SAFE_MODE_REQUIRED`.

## Storage

Produccion esperada:

```text
/data/continuous_evolution_os
```

DB de negocio:

```text
/data/database.db
```

El endpoint escribe solo almacenamiento propio de Continuous Evolution. No usa la DB de negocio para Product Memory.

## Render Cron recomendado

Nombre:

```text
nemesis-continuous-evolution
```

Schedule:

```text
*/15 * * * *
```

Command:

```text
python tools/render_cron_continuous_evolution_tick.py
```

Environment del Cron:

```text
PUBLIC_BASE_URL=https://bot-apuestas-crgf.onrender.com
AUTOMATION_SECRET=<sync false / secreto compartido con Web Service>
```

Environment del Web Service:

```text
CONTINUOUS_EVOLUTION_SAFE_MODE=1
CONTINUOUS_EVOLUTION_STORAGE_ROOT=/data/continuous_evolution_os
DB_PATH=/data/database.db
```

## QA local

Resultado de `tests/test_continuous_evolution_os.py`:

```text
18 passed
```

Cobertura especifica nueva:

- NO SECRET -> 403.
- Query secret -> 403.
- BAD SECRET -> 403.
- SAFE MODE OFF -> blocked.
- BAD STORAGE -> blocked.
- GOOD CONFIG -> PASS.
- SECOND RUN -> SKIPPED_NOT_DUE.
- CONCURRENT LOCK -> SKIPPED_ALREADY_RUNNING.
- Runner stateless sin secret -> error seguro sin disco ni red.

## Estado final

Produccion no modificada.
Render no modificado.
Cron no creado.
Telegram: 0.
Stripe: 0.
Push: 0.
Deploy: 0.

Resultado: READY_FOR_PRODUCTION_SCHEDULER_APPROVAL.
