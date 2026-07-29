# Observability Report

## Resumen

- Observabilidad local: `PASS`.
- Sentinel/AutoPilot integrados: true.
- Incidencias actuales en snapshot: 7.
- Produccion/logs externos: no certificados en este sprint.

## Observability

| Item | Valor | Estado evidencia | Fuente |
| --- | --- | --- | --- |
| Sentinel | READY | CONFIRMADO | engines y data/runtime |
| Errores recientes | No certificados en produccion | BLOQUEADO_POR_ACCESO | Render logs no consultados |
| Latencias | Locales/Browser QA | NO_CERTIFICADO | QA local |
| Eventos criticos | Incidencias del snapshot | CONFIRMADO | Operations Center |

## Seguridad

| Item | Valor | Estado evidencia | Fuente |
| --- | --- | --- | --- |
| Secret Guard | Presente | CONFIRMADO | automation_workforce |
| Privacy report | Disponible | CONFIRMADO | reports |
| Secret findings | 0 | CONFIRMADO | Privacy/Secret Guard |
| CSRF/admin | Protegido por sesion y token en acciones POST | CONFIRMADO | app.py |
| Rate limit/headers | Configuracion local presente; produccion pendiente | NO_CERTIFICADO | app.py/Render |

## Incidencias y certificaciones pendientes

| ID | Severidad | Titulo | Evidencia | Siguiente accion |
| --- | --- | --- | --- | --- |
| OPS-1F4754FBD1 | medium | Render y deploy | BLOQUEADO_POR_ACCESO | Certificar /api/runtime-version de Render en modo lectura. |
| OPS-A5101FAD77 | high | Backup y restore | NO_CERTIFICADO | Crear copia offsite y ejecutar restore aislado autorizado. |
| OPS-3B1F5138A0 | high | Cron y automatizacion | NO_CERTIFICADO | Ejecutar dry-run protegido y certificar ultimo/proximo tick. |
| OPS-18D60DB1E5 | high | Telegram | NO_CERTIFICADO | Certificar webhook, dry-run, dedupe y destino autorizado sin envio masivo. |
| OPS-89A275D482 | critical | Stripe y membresias | NO_CERTIFICADO | Certificar productos, precios y webhook de forma no destructiva. |
| OPS-43C082EBFE | high | Datos deportivos | NO_CERTIFICADO | Certificar frescura, completitud, stale y falsos live con timestamps reales. |
| OPS-0211D92412 | high | Continuidad operativa | NO_CERTIFICADO | Completar simulacro, offsite y handoff de segundo operador. |

## Guardrails

- no_deploy
- no_push
- no_real_telegram
- no_stripe_actions
- no_production_db_write
- no_paid_provider_call

## QA final ejecutada

- py_compile: PASS.
- compileall app.py/engines/tools/tests: PASS.
- pytest completo: PASS con `--basetemp=tmp/pytest-operations-center -p no:cacheprovider` tras un primer bloqueo de permisos en Temp global de Windows.
- Operations Center check: PASS.
- Sentinel: PASS, score 10.0/10, 0 issues abiertos, 0 criticos, 0 enlaces rotos.
- Privacy/Secret Guard: PASS, 1049 archivos revisados, 0 secretos confirmados, 0 hallazgos privacy, valores impresos false.
- Imports/rutas: PASS, 686 rutas, missing_templates=[], missing_static=[].
- Route/link audit: PASS, 738 rutas registradas, unsafe_smoke_count=0, direct_api_hrefs=21.
- Browser QA: PASS, 72 checks, average_experience_score=100.0, failures=[].
- Produccion modificada: false.
- Telegram enviado: false.
- Stripe ejecutado: false.
- Push/deploy/commit: false.

