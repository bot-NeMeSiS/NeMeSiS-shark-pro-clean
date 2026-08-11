# NEMESIS X PRODUCTION SCHEDULER CERTIFICATION

Estado: READY_LOCAL_NOT_ACTIVATED.
Fecha Madrid: 2026-08-11.

## Runner auditado

Archivo: `tools/run_continuous_evolution_scheduler.py`.

Resultado:

- Idempotente: SI, usa due/not-due por periodo Europe/Madrid.
- Europe/Madrid: SI, politica canonica en el motor.
- No requiere Flask persistente: SI, es CLI independiente.
- Scheduler externo compatible: SI.
- No imprime secretos: SI, output compacto y sanitizado por defecto.
- No Telegram: SI, guardrail `NO_TELEGRAM=true`.
- No Stripe: SI, guardrail `NO_STRIPE=true`.
- No deploy: SI, guardrail `NO_DEPLOY=true`.
- No muta negocio real: SI, solo escribe runtime propio del Continuous Evolution OS.
- Exit code: 0 si `ok` no es false; 1 si safe preflight bloquea.

## Safe Mode

Para cualquier `SCHEDULED_PRODUCTION` es obligatorio:

```bash
CONTINUOUS_EVOLUTION_SAFE_MODE=1
```

Bloqueos certificados localmente:

- Sin Safe Mode: `SAFE_MODE_REQUIRED`.
- Con `--force` en produccion: `FORCE_NOT_ALLOWED_IN_PRODUCTION`.
- Sin storage persistente: `PERSISTENT_STORAGE_REQUIRED`.
- Usando `data/runtime` del repo en produccion: `EPHEMERAL_STORAGE_BLOCKED`.

## Storage

Storage local por defecto:

```text
data/runtime/continuous_evolution_os
```

Storage recomendado en Render:

```text
/data/continuous_evolution_os
```

Resolucion automatica:

1. `--storage-root` si se pasa explicitamente.
2. `CONTINUOUS_EVOLUTION_STORAGE_ROOT` si existe.
3. En `SCHEDULED_PRODUCTION`, directorio padre de `DB_PATH` + `/continuous_evolution_os`.

No se toca la DB de negocio. Si se usa `/data`, el contenido debe quedar en namespace propio:

```text
/data/continuous_evolution_os/
```

Estado: PARTIAL hasta confirmar que `/data` es disco persistente activo en Render.

## Politica temporal

Timezone oficial: Europe/Madrid.

- Daily Product Review: 04:00.
- Daily Founder Brief: 04:05, generado por Daily Product Review.
- Weekly Executive Review: lunes 04:30.
- Monthly Strategy Review: dia 1, 05:00.

## Plan Render Cron

No usar UTC fijo diario porque fallaria con DST. Usar cron frecuente y dejar que el runner decida si toca ejecutar.

Cron recomendado:

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

El cron puede invocar cada 15 minutos. El runner ejecutara `PASS` solo cuando este due en Madrid y devolvera `SKIPPED_NOT_DUE` en el resto.

## Observabilidad de cada job

Cada job registra:

- job_id.
- trigger.
- scheduled_for y scheduled_for_utc.
- started_at y started_at_utc.
- finished_at y finished_at_utc.
- duration_ms.
- status.
- run_id.
- snapshot_id.
- founder_brief_id.
- codex_ready_count.
- error_safe sanitizado.
- next_expected_run y next_expected_run_utc.
- dangerous_actions_executed=false.

## Evidencia local Phase 02

- `SCHEDULED_PRODUCTION` sin Safe Mode: bloqueado con `SAFE_MODE_REQUIRED`.
- `SCHEDULED_PRODUCTION` con storage `data/runtime`: bloqueado con `EPHEMERAL_STORAGE_BLOCKED`.
- `SCHEDULED_PRODUCTION` con Safe Mode y storage temporal aislado: PASS local.
- Output por defecto: compacto y sanitizado.
- Telegram: 0.
- Stripe: 0.
- Deploy: 0.

## Activacion

No activada en esta ejecucion.

Para activar se requiere:

1. Commit local Phase 02.
2. Push controlado a origin/main.
3. Confirmar disco persistente `/data` en Render.
4. Crear solo el cron `nemesis-continuous-evolution`.
5. Configurar `CONTINUOUS_EVOLUTION_SAFE_MODE=1`.
6. Configurar `CONTINUOUS_EVOLUTION_STORAGE_ROOT=/data/continuous_evolution_os`.
7. Comprobar primer dry-run o primer job real.
8. Iniciar seguimiento DAY 1 / DAY 2 / DAY 3.
