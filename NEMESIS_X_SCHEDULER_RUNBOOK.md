# NEMESIS X SCHEDULER RUNBOOK

Estado: READY_FOR_PRODUCTION_SCHEDULER_APPROVAL_LOCAL.
Fecha Madrid: 2026-08-27.

## Root cause

Render Cron Jobs no deben ejecutar directamente `python tools/run_continuous_evolution_scheduler.py` para Continuous Evolution porque el job no comparte el persistent disk del web service. Eso impediria conservar snapshots, Product Memory, Founder Briefs y Prepared for Codex como memoria real.

## Arquitectura canonica

```text
RENDER CRON
-> HTTPS POST
-> WEB SERVICE NEMESIS
-> /api/automation/continuous-evolution/tick
-> Continuous Evolution safe runner
-> /data/continuous_evolution_os
```

El Cron es stateless. El Web Service mantiene el estado en su persistent disk.

## Endpoint protegido

Ruta:

```text
POST /api/automation/continuous-evolution/tick
```

Autenticacion:

```text
X-Automation-Secret: <AUTOMATION_SECRET>
```

No se acepta `secret` por URL. Sin header o con header incorrecto devuelve 403.

## Variables del Web Service

Obligatorias antes de activar el cron externo:

```text
CONTINUOUS_EVOLUTION_SAFE_MODE=1
CONTINUOUS_EVOLUTION_STORAGE_ROOT=/data/continuous_evolution_os
DB_PATH=/data/database.db
```

El endpoint falla cerrado si:

- Safe Mode no esta activo.
- Storage no existe o no puede escribirse.
- Storage apunta a `data/runtime` del repo.
- Storage productivo no esta bajo `/data/continuous_evolution_os`.

## Runner stateless para Render Cron

Archivo:

```text
tools/render_cron_continuous_evolution_tick.py
```

Comando recomendado para el Cron Job:

```text
python tools/render_cron_continuous_evolution_tick.py
```

Variables del Cron Job:

```text
PUBLIC_BASE_URL=https://bot-apuestas-crgf.onrender.com
AUTOMATION_SECRET=<mismo secreto que el Web Service>
```

El runner no necesita persistent disk. No ejecuta Continuous Evolution localmente. Solo hace POST HTTPS al web service con cabecera segura.

## Cadencia

No usar UTC fijo diario por DST. Configurar el Cron externo frecuente y dejar que el endpoint decida due/not-due en Europe/Madrid.

Recomendado:

```text
*/15 * * * *
```

La politica interna ejecuta:

- Daily Product Review: 04:00 Europe/Madrid.
- Daily Founder Brief: generado por Daily Product Review.
- Weekly Executive Review: lunes 04:30 Europe/Madrid.
- Monthly Strategy Review: dia 1, 05:00 Europe/Madrid.

## Estados esperados

- `PASS`: ejecucion debida completada.
- `PARTIAL`: fallo controlado con memoria preservada.
- `SKIPPED_NOT_DUE`: invocacion valida, no toca ejecutar.
- `SKIPPED_ALREADY_RUNNING`: lock activo.
- `SKIPPED_PAUSED`: pausa administrativa activa.
- `SAFE_MODE_REQUIRED`: Safe Mode ausente.
- `PERSISTENT_STORAGE_REQUIRED`: storage no aprobado.
- `STORAGE_WRITE_BLOCKED`: el web service no pudo usar storage.

## Guardrails

El endpoint permite solo:

- OBSERVE
- ANALYZE
- COMPARE
- WRITE PRODUCT MEMORY
- WRITE SNAPSHOT
- GENERATE PRODUCT REVIEW
- GENERATE EXECUTIVE REVIEW
- GENERATE FOUNDER BRIEF
- PREPARE FOR CODEX

El endpoint no puede:

- modificar codigo
- hacer commit
- hacer push
- hacer deploy
- enviar Telegram
- llamar Stripe
- publicar contenido
- activar campanas
- gastar dinero
- modificar usuarios
- modificar membresias
- ejecutar comandos arbitrarios
- aceptar shell input
- aceptar paths arbitrarios

## QA local certificado

- Sin secret: 403.
- Secret por URL: 403.
- Secret incorrecto: 403.
- Safe Mode off: blocked.
- Storage repo runtime: blocked.
- Configuracion buena local: `PASS`.
- Segunda invocacion: `SKIPPED_NOT_DUE`.
- Lock activo: `SKIPPED_ALREADY_RUNNING`.
- Telegram: 0.
- Stripe: 0.
- Deploy: 0.
- Push: 0.

## Activacion pendiente

No activado todavia.

Para produccion:

1. Revisar y aprobar esta arquitectura.
2. Hacer push/deploy del endpoint si aun no esta en origin/main/Render.
3. Configurar variables del Web Service.
4. Crear solo el Cron `nemesis-continuous-evolution` con el runner stateless.
5. Observar primera invocacion real.
6. Iniciar evidencia DAY 1 / DAY 2 / DAY 3 sin simular fechas.
