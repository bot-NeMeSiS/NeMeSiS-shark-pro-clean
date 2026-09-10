# Platform

OPS-001 BLOCKED (publicacion), OPS-002 QA (higiene), OPS-003 BLOCKED (retirada adicional).
No cambios de Render, cron, secrets, DB_PATH, cuotas o planes.

## Automatizacion actual y ultima evidencia

| Pieza | Existente / conectado | Ultima evidencia | Estado actual |
|---|---|---|---|
| Master runner | tools/render_cron_master_tick.py | Cron telegram-auto-tick registrado historicamente | NOT_TESTED hoy; archivo intacto |
| Continuous Evolution | engines/product_review_system_engine.py y runner existente | PASS/NOT_DUE historico | NOT_TESTED hoy; no activacion desde docs |
| Telegram | Orquestado por cron existente | OLD_MATCH historico | No envio iniciado por CX |
| Receptor COORD-8-AUTO-01 R1 | Encargo previo | BLOQUEADO_ACTIVACION | No instalado/activado por CX |
| Sports observacion | DAY 1-5 conservados | DAY 5 2026-09-08 | No se cambia programacion ni se inventa escucha |

Las nueve tareas ChatGPT historicas no tienen IDs/configuraciones actuales
verificados en CX: NOT_TESTED, no nueve tareas activas certificadas. La anterior
observacion de un heartbeat deportivo tampoco acredita vigencia hoy.
El [indice historico de tareas](../../NEMESIS_CONTROL_PROYECTO/TAREAS_PROGRAMADAS_Y_VIGILANCIA.md)
conserva nombres/propuestas; no se renombra ni reprograma ninguna tarea aqui.

Render MCP sin workspace confirmado: no se puede afirmar nuevo SHA LIVE ni
estado de workers. Confirmar `NeMeSiS's workspace` es el requisito de lectura.
No se toman correos, credenciales o env vars para resolverlo.

## Inventario y deuda comprobada

- 4122 tracked; 225.483.002 bytes de archivos versionados, NO tamano de release ZIP.
- 947 fuentes Python tracked; 157 engines; 630 archivos tools; app.py 31.624 lineas.
- Clasificacion privada por archivo: 523 CANONICAL, 2499 HISTORICAL,
  9 SUPERSEDED por autoridad operativa, 317 RUNTIME, 774 UNKNOWN.
- 142 grupos byte-identicos se retienen por posibles contratos de ruta.
- Seis temporales historicos inaccesibles: no se inventaria interior ni modifica ACL.
- .venv, release_output y entornos existentes se conservan; no clon/copia integral.

## Higiene segura

Retirados 393 .pyc (11.162.408 bytes) de dos caches propias de SE terminado,
hash/ubicacion revisados; 0 tracked eliminados. XML, before, reports, DAY y fuentes
se conservan. No borrar memoria Product/CE ni data/runtime por parecer regenerable.

.gitignore bloquea temporales QA conocidos y caches. No quita archivos ya tracked
ni protege ante `git add -f`; revision de staging/PR sigue obligatoria.
Empaquetador existente: tools/build_clean_release.py, auditor tools/audit_release_zip.py.
No importarlos para inspeccion: build_clean_release tiene efectos de filesystem
al importar. No ZIP generado. Project_control no se agrega al paquete de app por rutina.
No se modifica el allowlist historico. Se corrige solo include: exclusiones
comunes antes de aceptar reports/runtime. Reproduccion 10 FAIL -> 24/24 PASS;
seleccion identica para todos los tracked. Las excepciones runtime existentes
siguen explicitas; no se retiran por parecer regenerables.

Futuro: rama + PR + checks existentes, sin bypass de protecciones ni doble deploy.
Las excepciones historicas de preflight/qa/smoke no son permisos reutilizables.
