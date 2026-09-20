# Conversation Index

Indice operativo, no transcripcion ni cola alternativa. Actualizado 2026-09-19.
Solo fuentes disponibles DENTRO de este proyecto. No se abren conversaciones
externas ni se inventa el contenido del mapa privado C03-C21 mencionado por
un informe. Ese mapa y los adjuntos ausentes no son fuentes recuperadas aqui.

## Conocimiento recuperado

| Tema / fecha de fuente | Decisiones vigentes | Implementacion derivada / evidencia | Autoridad desplazada | Pendiente vivo / cola |
|---|---|---|---|---|
| Fases, V944 y V946 / historial 2026-09 | Match Context existente; V946 no se infiere por numero | [Historial](../NEMESIS_CONTROL_PROYECTO/HISTORIAL_CONVERSACIONES_Y_FASES.md), app.py, engines/match_context_engine.py | La auditoria de julio dejaba V944 sin verificar | V946 sin especificacion; CX-005, OPS-003 |
| SE-01 / 2026-09-09 | PASS_LOCAL_SCOPE; doce positivos no certificados; conservar DAY 3/4/5 | [Alineacion y SE-01](../reports/NEMESIS_OFFICIAL_VISUAL_REFERENCE_ALIGNMENT_REPORT.md), services/sports_service.py | No trasladar el SHA/PR/CI de ese cierre a hoy | QA-001, SP-001, DATA-001 |
| Visual H01-H09 / 2026-09-07 | REF-12 Match Center; H07 no aprobado | [Cierre H01-H09](../reports/NEMESIS_OFFICIAL_VISUAL_REFERENCE_ALIGNMENT_REPORT.md#cierre-consolidado-h01-h09---2026-09-07-historico-preservado), 16 PNG reference_images | Pruebas historicas no acreditan todo el candidato actual | UX-001, UX-003 |
| R8 y reanudacion / 2026-09-19 | Design congelado; recuperar diferencias versionadas, no instaladores | [Cierre local](../reports/LOCAL_CONTINUITY_20260919.md), commit 317ac8c3, Home/Calendar/Match, i18n/Madrid | R9 no certificado; no volver a la base visual antigua | UX-003, CX-003 |
| Sentinel operativo / 2026-09-19 | Trabajo durable, permisos, CSRF, executor cerrado; no cerrar incidencia por HTTP 200 | [Cierre local](../reports/LOCAL_CONTINUITY_20260919.md), engines/sentinel_jobs.py, tests/test_sentinel_jobs_http.py | Nombre de worker o mock no acredita ejecucion | OPS-001; publicacion no autorizada |
| Directo / 2026-09-19 | Score nullable, stale no LIVE, SCORE_UPDATE no GOAL; Madrid independiente del idioma | [Cierre local](../reports/LOCAL_CONTINUITY_20260919.md), engines/realtime_surface_adapter.py, static/v934-realtime.js | Quitar limite visual no prueba cobertura de proveedor | CX-003, CX-004, CX-005 |
| Telegram / V844, fecha no establecida | No relleno, dedupe, Madrid; sin envio real aqui | [Continuacion disponible](../CHATGPT_CONTINUATION_REPORT.md), filtro y master tick existentes | Plan en un informe no prueba cron ACTIVE | SP-001; permisos externos conservados |
| SHARK / V845-V847, fecha no establecida | Hechos/contexto/analisis/apuestas separados; esperar/no apostar son validos | [Continuacion](../reports/CHATGPT_CONTINUATION_REPORT.md), engines/shark_ai_product_assistant_engine.py | Integracion o API configurada no demuestra calidad ni permiso de gasto | CX-006, AI-001 |
| Soporte y membresias / 2026-09-19 | Entrega local verificable; manual/ADMIN/suscripcion vigente protegidos | [Cierre local](../reports/LOCAL_CONTINUITY_20260919.md), support_inbox_engine.py, stripe_payments_engine.py | No afirmar email enviado, Stripe real ni ELITE+ existente | CX-008, CX-010 |
| Higiene anterior / 2026-09-09 | Mantener evidencia y contratos; no purga por nombre o edad | [Control previo](../NEMESIS_CONTROL_PROYECTO/ESTADO_ACTUAL_PROYECTO.md), Git c4a81003:project_control/ACTIVE_WORK.md | Inventarios antiguos no son los conteos actuales | CX-002, OPS-002/003 |

## Arquitectura documental

- CANONICAL: MASTER_CONTROL es entrada; CURRENT_TRUTH hechos; DECISIONS decisiones; este indice conocimiento; LOCKED_CONTRACTS invariantes y domains especificaciones con fecha.
- ACTIVE: ACTIVE_WORK alcance inmediato; CODEX_QUEUE unica cola; BLOCKERS condiciones; RELEASE_STATE candidatos; ROADMAP estrategia subordinada.
- EVIDENCE: reports y certificaciones conservan revision/fecha/entorno. Presencia no equivale a prueba aprobada actual.
- HISTORICAL: NEMESIS_CONTROL_PROYECTO, NEMESIS_DOCUMENTACION y continuaciones fechadas. Conservan enlaces originales, no segunda cola.
- SUPERSEDED: docs/NEMESIS_RECONCILIATION_AUDIT.md como autoridad operativa; conservado como historia.
- UNKNOWN: documentos aun sin autoridad/procedencia suficientemente clasificada. Retener, no promover a CANONICAL ni borrar por defecto.

Los documentos operativos reemplazados conservan copia previa local en
data/local_dev/organization-20260919/before y version c4a81003 en Git.
No se movieron informes ni se cambiaron rutas usadas por imports/builds.
Clasificacion por archivo, hashes SOLO documentales, duplicados y limites:
data/local_dev/organization-20260919/inventory.json.

## Retencion y legacy

No se retira nada en esta fase. .env/DB/log se inventarian por metadatos sin leer
sus bytes; screenshots, XML, copias y parches se retienen. Duplicados documentales
por hash mantienen contratos de ruta; no autorizan borrado. Cache es candidato
solo despues de dependencias, procesos y capacidad de regeneracion comprobados.

Inventario legacy estatico: motores sin import, templates sin literal consumidor,
aliases de un mismo handler y helpers con cuerpo igual se clasifican REVIEW_ONLY.
Los imports dinamicos, entrypoints CLI, macros y enlaces externos siguen siendo
dependencias posibles. Cero referencia estatica NO significa cero consumidor.
Ejemplo: engines/__init__.py es inicializador de paquete, no un motor huerfano.

Para cada retirada futura: consumidor cero demostrado -> alternativa -> pruebas
positivas/negativas -> rollback claro. Ninguna retirada funcional ni worktree
esta aprobada por este indice. MAIN es la unica linea permanente objetivo;
candidatos con contenido unico permanecen protegidos.
