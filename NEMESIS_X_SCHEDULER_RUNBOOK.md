# NEMESIS X SCHEDULER RUNBOOK

## Politica temporal

Timezone oficial: Europe/Madrid.

- Daily Product Review: 03:15.
- Daily Founder Brief: 03:20, generado por el Daily Product Review.
- Weekly Executive Review: lunes 04:00.
- Monthly Strategy Review: dia 1, 04:30.

## Runner seguro

Archivo: `tools/run_continuous_evolution_scheduler.py`.

Dry run:

```powershell
.\.venv\Scripts\python.exe tools\run_continuous_evolution_scheduler.py --dry-run --task daily_product_review
```

Run local controlado:

```powershell
.\.venv\Scripts\python.exe tools\run_continuous_evolution_scheduler.py --task daily_product_review
```

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

## Activacion en Render

No activada en este sprint. Requiere autorizacion explicita y revision de seguridad antes de conectar cualquier cron productivo.
