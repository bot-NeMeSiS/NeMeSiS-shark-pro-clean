# 04 — Incidencias y hallazgos

## Abierto — HIGH — Sports Truth inconsistente entre superficies

Fecha detectada: 2026-09-04.

### Evidencia observada

- Se observaron partidos terminados o sin evidencia LIVE fresca publicados como `LIVE`.
- Caso destacado: Matagalpa vs UNAN Managua llegó a persistir como `1-0 · 88' · En directo` durante horas.
- La interfaz llegó a presentar `Confianza 100 / Alta` pese a inconsistencia/frescura dudosa.
- Home llegó a mostrar 0 directos mientras `/live` y `/calendar` todavía contabilizaban/publicaban un LIVE, demostrando inconsistencia transversal.

### Causa técnica identificada parcialmente

`api_football_live_snapshots` conserva snapshots entre sincronizaciones. La capa de experiencia LIVE no estaba propagando correctamente `last_synced_at` al contrato canónico de frescura V935.

### Hotfix aplicado

PR #6 / commit `fddbeea3b1205e2f05e62bcf95630a7a4c85a4cd`:

- `last_synced_at` pasa a servir de evidencia temporal para LIVE.
- snapshots stale/conflictivos se bloquean en la lectura del live cache.
- datos obsoletos pasan a `Datos retrasados` en vez de `En directo`.
- no se borraron snapshots ni datos de producción.

### Estado posterior

La monitorización posterior indicó que el síntoma podía seguir presente en alguna superficie. Esto sugiere que existe otra ruta/dataset/capa de presentación que no consume todavía la misma decisión canónica.

### Cierre requerido

No marcar como resuelto hasta verificar simultáneamente:

1. Home y su contador LIVE.
2. `/live`.
3. `/calendar`.
4. `/partidos`.
5. Match Center/detail.
6. SHARK cuando referencia estado del partido.
7. Cualquier badge/contador/alerta Telegram derivado de lifecycle.

Todas deben coincidir para el mismo `match_id` y timestamp.

## Positivo — Monitorización operativa

- Production Watch ha distinguido reinicios/deploys transitorios de caídas persistentes.
- Render ha podido confirmar build, arranque de Gunicorn y HTTP 200 tras hotfix.
- La vigilancia detectó que "deploy correcto" no equivale a "problema funcional resuelto", evitando un falso cierre.

## Regla nueva derivada del incidente

Nunca mostrar `Confianza 100 / Alta` si el estado está `STALE`, existe `status_conflict`, falta timestamp de evidencia o distintas superficies no coinciden en lifecycle/marcador/minuto.
