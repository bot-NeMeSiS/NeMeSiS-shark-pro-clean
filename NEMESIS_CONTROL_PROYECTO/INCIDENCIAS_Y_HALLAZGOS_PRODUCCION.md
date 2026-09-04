# INCIDENCIAS Y HALLAZGOS DE PRODUCCIÓN

## ABIERTA — HIGH — Sports Truth inconsistente entre superficies

Fecha detectada: 2026-09-04.

### Qué pasó
- Se observaron partidos terminados o sin evidencia LIVE reciente todavía publicados como `LIVE`.
- Caso destacado: Matagalpa vs UNAN Managua persistió como `1-0 · 88' · En directo` durante horas.
- La interfaz llegó a mostrar `Confianza 100 / Alta` pese a frescura o consistencia dudosa.
- Home llegó a mostrar 0 directos mientras `/live` y `/calendar` todavía publicaban/contabilizaban uno.

### Causa técnica identificada parcialmente
`api_football_live_snapshots` conserva snapshots entre sincronizaciones. La capa LIVE no estaba propagando correctamente `last_synced_at` al contrato canónico de frescura V935.

### Hotfix aplicado
PR #6 / commit `fddbeea3b1205e2f05e62bcf95630a7a4c85a4cd`:
- `last_synced_at` pasa a servir de evidencia temporal.
- snapshots stale/conflictivos se bloquean en lectura LIVE.
- datos obsoletos pasan a `Datos retrasados` en vez de `En directo`.
- no se borraron snapshots ni datos de producción.

### Estado posterior
La monitorización posterior indicó que alguna superficie podía seguir mostrando el síntoma, lo que apunta a otra ruta/dataset/capa que aún no consume la misma decisión canónica.

### Para cerrar esta incidencia hay que validar simultáneamente
1. Home y contador LIVE.
2. `/live`.
3. `/calendar`.
4. `/partidos`.
5. Match Center/detail.
6. SHARK cuando usa estado del partido.
7. Cualquier badge, contador o alerta Telegram derivada del lifecycle.

Todas deben coincidir para el mismo `match_id` y timestamp.

## Hallazgo positivo
- La vigilancia distingue reinicios/deploys transitorios de caídas persistentes.
- Un deploy correcto ya no se considera automáticamente una incidencia resuelta: se valida después el comportamiento público.

## Regla derivada
Nunca mostrar `Confianza 100 / Alta` si el dato está `STALE`, existe `status_conflict`, falta timestamp de evidencia o distintas superficies no coinciden.
