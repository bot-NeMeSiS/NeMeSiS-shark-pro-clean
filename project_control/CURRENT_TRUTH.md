# Current Truth

Actualizacion: 2026-09-20. Autoridad: GitHub main + Render observado. Sin PII ni secretos.

## Identidad actual

- GitHub `main`: `7a1ba50bf9d6fec8648fcacc2dae72b7cbe730ba`.
- Origen: merge de PR #16, candidato reconciliado del 19/09.
- PR #16: MERGED.
- PR #14 Directo: CLOSED / SUPERSEDED por main; su frente funcional sigue abierto a validacion real.
- PR #15 integracion Sentinel: CLOSED / SUPERSEDED por PR #16.
- Render web `nemesissharkpro`: LIVE en el SHA exacto `7a1ba50b...`.
- Render cron `telegram-auto-tick`: LIVE en el mismo SHA.

## Evidencia verificada

- CI push sobre main: NeMeSiS CI QA = SUCCESS.
- Smoke push sobre main = SUCCESS.
- Render Deploy Guard: preflight = SUCCESS; certify-production sigue en PRODUCTION_VALIDATION mientras completa sus ventanas de observacion.
- Preflight incluye compilacion, Jinja, V944, controles criticos, navegacion, Continuous Sentinel, Secret Guard, auditoria de rutas y release identity.
- Produccion observada tras deploy: `/`, `/calendar`, `/live`, `/picks`, `/shark`, `/api/runtime-version`, `/api/health`, `/api/realtime/sports`, `/manifest.json` y `/service-worker.js` responden sin 5xx en las muestras revisadas.
- No se observaron Traceback, ERROR, Exception, 500, 502 ni 503 desde el deploy revisado.
- Cron real: ejecuciones `overall=PASS`; Telegram registro al menos una ejecucion `SENT` y ejecuciones posteriores con dedupe/OLD_MATCH.
- API-Football deep/provider permanece PARTIAL / ACCESS_FAILED en la ultima muestra persistida; freshness profunda sigue NOT_ESTABLISHED. No se reetiqueta como certificado.

## Sentinel

- Codigo Sentinel y project control estan integrados en main.
- El runner de escritorio sigue siendo LOCAL SAFE: no se convierte en executor productivo por estar desplegado.
- CI separa los tests LOCAL SAFE/Sentinel en procesos aislados sin retirar la suite estandar.
- OPS-001 queda DONE_LOCAL_SAFE: cierre formal en `reports/SENTINEL_OPERATIONAL_CLOSURE_20260920.md`.
- No se autoriza por este documento escritura automatica en produccion, DB real, pagos, proveedores o Telegram fuera de los flujos ya existentes.

## Directo / Sports Reality

Prioridad interna activa tras el cierre de Sentinel.

- La funcionalidad de actualizacion en pagina abierta ya esta integrada en main y supera el antiguo PR #14.
- Main conserva marcador nullable, minuto 0/descuento, caducidad LIVE, proteccion frente a respuestas antiguas y actualizacion hacia finalizados.
- Main ademas incorpora localizacion, `SCORE_UPDATE` factual y tests HTTP ampliados.
- Esto NO certifica feed real universal, cobertura, Safari/iPhone fisico ni proveedor profundo.

## Diseño

- El frente Design/R9 sigue PRESERVE / NOT_CERTIFIED.
- No se considera resuelto por el merge de PR #16.
- La conformidad global con referencias y H07 siguen pendientes de decision/evidencia.

## Otros limites abiertos

- `/app`: rendimiento productivo historico sigue siendo un frente a medir; no se declara resuelto por este deploy.
- Stripe/pagos externos: NOT_CERTIFIED.
- ELITE+: contrato no definido.
- Doce positivos SE-01 y bloqueos ambientales historicos conservan su clasificacion; no se convierten en PASS global.
