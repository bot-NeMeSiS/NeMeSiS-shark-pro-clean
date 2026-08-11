# NEMESIS X SCHEDULER RUNBOOK

## Politica temporal

Timezone oficial: Europe/Madrid.

- Daily Product Review: 04:00.
- Daily Founder Brief: 04:05, generado por el Daily Product Review.
- Weekly Executive Review: lunes 04:30.
- Monthly Strategy Review: dia 1, 05:00.

## Runner seguro

Archivo: `tools/run_continuous_evolution_scheduler.py`.

Dry run local:

```powershell
.\.venv\Scripts\python.exe tools\run_continuous_evolution_scheduler.py --dry-run --task daily_product_review
```

Run local controlado:

```powershell
.\.venv\Scripts\python.exe tools\run_continuous_evolution_scheduler.py --task daily_product_review
```

Dry run productivo seguro con storage persistente:

```bash
CONTINUOUS_EVOLUTION_SAFE_MODE=1 \
CONTINUOUS_EVOLUTION_STORAGE_ROOT=/data/continuous_evolution_os \
python tools/run_continuous_evolution_scheduler.py --dry-run --trigger SCHEDULED_PRODUCTION
```

Run productivo seguro:

```bash
CONTINUOUS_EVOLUTION_SAFE_MODE=1 \
CONTINUOUS_EVOLUTION_STORAGE_ROOT=/data/continuous_evolution_os \
python tools/run_continuous_evolution_scheduler.py --trigger SCHEDULED_PRODUCTION
```

## Safe Mode

`SCHEDULED_PRODUCTION` requiere obligatoriamente:

```text
CONTINUOUS_EVOLUTION_SAFE_MODE=1
```

Bloqueos esperados:

- `SAFE_MODE_REQUIRED` si falta Safe Mode.
- `FORCE_NOT_ALLOWED_IN_PRODUCTION` si se usa `--force` con produccion.
- `PERSISTENT_STORAGE_REQUIRED` si no hay storage persistente.
- `EPHEMERAL_STORAGE_BLOCKED` si se intenta usar `data/runtime` del repo.

## Storage

Local por defecto:

```text
data/runtime/continuous_evolution_os
```

Produccion recomendada:

```text
/data/continuous_evolution_os
```

No usar `data/runtime` en Render. El runner puede derivar `/data/continuous_evolution_os` desde `DB_PATH=/data/database.db`, pero se recomienda configurar `CONTINUOUS_EVOLUTION_STORAGE_ROOT` de forma explicita.

## Guardrails

Siempre activos:

- READ_ONLY_OPERATIONS;
- NO_TELEGRAM;
- NO_STRIPE;
- NO_DEPLOY;
- NO_EXTERNAL_MARKET_RESEARCH;
- NO_PRODUCTION_MUTATION.

## Estados esperados

- PASS: ejecucion completa.
- PARTIAL: fallo controlado con memoria preservada.
- SKIPPED_NOT_DUE: ya existe ejecucion para el periodo.
- SKIPPED_ALREADY_RUNNING: lock activo.
- SKIPPED_PAUSED: automatizacion pausada por admin.
- UNKNOWN_TASK: tarea no reconocida.

## Pause / Resume

Desde Founder Center:

- Pausar evolucion: bloquea ejecuciones programadas.
- Reanudar evolucion: permite futuras ejecuciones programadas.

La pausa no afecta Sports Core, clientes, Telegram, Stripe ni app normal.

## Failure recovery

Si una ejecucion falla antes de crear snapshot, el ultimo snapshot bueno permanece como latest_snapshot.
Si un componente falla dentro del ciclo, la ejecucion queda PARTIAL_WITH_UNAVAILABLE_COMPONENTS y Product Memory se conserva.

## Render Cron recomendado

No usar UTC fijo diario por DST. Configurar cron frecuente y dejar que el runner decida si toca ejecutar por Europe/Madrid.

```yaml
- type: cron
  name: nemesis-continuous-evolution
  runtime: python
  schedule: "*/15 * * * *"
  buildCommand: pip install -r requirements.txt
  startCommand: python tools/run_continuous_evolution_scheduler.py --trigger SCHEDULED_PRODUCTION
  envVars:
    - key: CONTINUOUS_EVOLUTION_SAFE_MODE
      value: "1"
    - key: CONTINUOUS_EVOLUTION_STORAGE_ROOT
      value: /data/continuous_evolution_os
    - key: DB_PATH
      value: /data/database.db
```

No activado todavia. Requiere push controlado, confirmacion de storage persistente y autorizacion de infraestructura.
