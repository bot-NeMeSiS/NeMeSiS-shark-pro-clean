# Current Truth

Actualizacion: 2026-09-20. Autoridad: GitHub main + Render observado. Sin PII ni secretos.

## Identidad actual

- GitHub `main`: `cc6c7dfc33eb2909adb2c66e5b7175e330e2f1d0`.
- Origen: merge de PR #16, candidato reconciliado del 19/09.
- PR #16: MERGED.
- PR #19: MERGED; Calendario hidrata resultados persistidos para fechas pasadas mediante lectura SQLite sin nuevas llamadas a proveedor.
- PR #14 Directo: CLOSED / SUPERSEDED por main; su frente funcional sigue abierto a validacion real.
- PR #15 integracion Sentinel: CLOSED / SUPERSEDED por PR #16.
- Render web `nemesissharkpro`: LIVE en el SHA exacto `cc6c7dfc...`.
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

## Calendar history follow-up

- PR #23: MERGED en `cc6c7dfc33eb2909adb2c66e5b7175e330e2f1d0`.
- Finalizados y Resultados respetan la fecha seleccionada.
- `/api/calendar` hidrata el mismo histórico persistido que la página.
- El contador de Finalizados es date-scoped.
- El estado visible de proveedor/calendario se calcula sobre el resumen ya hidratado.
- Fuente histórica: SQLite persistida read-only; 0 llamadas nuevas a proveedor y 0 escrituras de DB desde render.
- Track Record/ROI permanece separado.
- Resultado pendiente no se convierte en 0-0.
- Web y cron Render están LIVE en el SHA actual; barrido inicial sin 500/502/503/Traceback/ERROR.

## Calendar history follow-up

- PR #23: MERGED en `cc6c7dfc33eb2909adb2c66e5b7175e330e2f1d0`.
- Finalizados y Resultados respetan la fecha seleccionada.
- `/api/calendar` hidrata el mismo histórico persistido que la página.
- El contador de Finalizados es date-scoped.
- El estado visible de proveedor/calendario se calcula sobre el resumen ya hidratado.
- Fuente histórica: SQLite persistida read-only; 0 llamadas nuevas a proveedor y 0 escrituras de DB desde render.
- Track Record/ROI permanece separado.
- Resultado pendiente no se convierte en 0-0.
- Web y cron Render están LIVE en el SHA actual; barrido inicial sin 500/502/503/Traceback/ERROR.

## Sports Reality diagnostics — PR #26

- PR #26 MERGED en `cc6c7dfc33eb2909adb2c66e5b7175e330e2f1d0`.
- Web y cron Render observados LIVE sobre el mismo SHA.
- La app distingue ahora fuente de la ventana actual, contribucion efectiva, cache reutilizada y frescura del acceso al proveedor.
- Evidencia historica de API-Football no puede presentarse como acceso actual: `provider_access_is_current` y `provider_access_freshness` lo separan explicitamente.
- Live y Odds se diagnostican por separado de la fuente principal.
- Los errores se exponen solo mediante reason codes saneados.
- Falta registrar el primer tick de cron posterior al deploy para conocer la fuente REAL actual observada. Hasta entonces no se asigna una fuente concreta.

## REAL_PRODUCTION Sports Reality — 12:55 Madrid

Primer tick ejecutado despues de PR #26 sobre `cc6c7dfc33eb2909adb2c66e5b7175e330e2f1d0`:

- master cron: `overall=PASS`.
- fuente de ventana actual: `SPORTSDB_FALLBACK`.
- SportsDB: `used=true`, `data_contributed=true`, `processed=180`, `ok=true`.
- API-Football primary: `used=false`, `data_contributed=false`, `fixtures_count=0`, `state=ERROR`, `reason_code=PROVIDER_ERROR`.
- acceso API-Football: `provider_access_is_current=false`, `provider_access_freshness=LAST_OBSERVED_NOT_CURRENT`; la observacion de acceso del 10/09 es historica, no prueba acceso actual.
- Live: ejecuto 1 llamada y 0 fixtures; devolvio resultado util/parcial, pero registro error.
- Odds: ejecuto 14 llamadas, 0 procesados y registro error.
- Se detecto defecto diagnostico: etapas `ok=true` con errores quedaban `reason_code=NONE`. PR #29 corrige esa contradiccion; hasta su validacion/merge no se da Sports Reality por cerrado.
