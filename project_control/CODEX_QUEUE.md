# Codex Queue

Unica cola. Actualizada 2026-09-19. Un ID por trabajo; aliases no crean otra tarea.
Estados conservados: BACKLOG, READY, IN_PROGRESS, BLOCKED, QA, PRODUCTION_VALIDATION, DONE, WONT_DO.
Responsable es un rol asignado, no prueba de worker activo. UNASSIGNED indica falta de asignacion.
QA significa pendiente de revisar el candidato; DONE siempre conserva su alcance.
Evidencia apunta a fuente disponible, no a certificacion del arbol presente.
Los bloqueos se definen una sola vez en BLOCKERS.md. Leer no concede permisos.

<!-- queue:start -->
| ID | Alias | Estado | Responsable | Ambito | Bloqueo | Evidencia | Siguiente |
|---|---|---|---|---|---|---|---|
| CX-001 | CX-SE-01 / COORD-8-SE-01 R1 | DONE | Codex / QA | PASS_LOCAL_SCOPE | ENV | reports/NEMESIS_OFFICIAL_VISUAL_REFERENCE_ALIGNMENT_REPORT.md | Preservar SE-01 y sus doce positivos no certificados |
| CX-002 | CX-ORG-01 | QA | Codex | LOCAL_ONLY | LEGACY | project_control/CONVERSATION_INDEX.md | Revisar consolidacion e inventario; ninguna purga autorizada |
| CX-003 | CX-RESULTS-01 / COORD-8-RESULTS-01 R1 | QA | Codex / Datos | LOCAL_ONLY | EXTERNAL,PUBLISH | reports/LOCAL_CONTINUITY_20260919.md | Replay FINAL_OVERRIDES_STALE_LIVE_V1 10/10 y cinco superficies; feed/produccion/eventos/stats completos no certificados |
| CX-004 | CX-DATA-01 | BLOCKED | Datos / Founder | NOT_TESTED | EXTERNAL | project_control/domains/DATA.md | Piloto real autorizado y cobertura; no otro proveedor |
| CX-005 | CX-INTELLIGENCE-01 | QA | Codex / Sports UX | LOCAL_ONLY | EXTERNAL | reports/LOCAL_CONTINUITY_20260919.md | Match Context preserva descuento/periodo; comprobar datos reales solo bajo autorizacion |
| CX-006 | CX-SHARK-01 | QA | Codex / SHARK | LOCAL_ONLY | EXTERNAL | reports/LOCAL_CONTINUITY_20260919.md | WAIT/NO_BET trazables sin confianza inventada; modelo y vigencia de cuotas pendientes |
| CX-007 | CX-MEDIA-01 | BLOCKED | Datos / Founder | NOT_TESTED | EXTERNAL | project_control/domains/DATA.md | Evidencia de derechos y cobertura antes de activacion |
| CX-008 | CX-PLANS-01 | QA | Codex / Negocio | LOCAL_ONLY | COMMERCIAL | reports/LOCAL_CONTINUITY_20260919.md | Expiracion no degrada ADMIN; gating FREE/PRO/ELITE probado; ELITE+ no definido |
| CX-009 | CX-ANALYTICS-01 | BACKLOG | Negocio / Datos | NOT_TESTED | EXTERNAL | project_control/domains/BUSINESS.md | Definir metricas sobre datos reales; no inventar ingresos |
| CX-010 | CX-STRIPE-01 | BLOCKED | Negocio / Founder | LOCAL_SAFE_BLOCKED | COMMERCIAL | reports/LOCAL_CONTINUITY_20260919.md | Local seguro preservado; validar ciclo externo autorizado antes de cobros |
| CX-011 | CX-FIRST10-01 | BACKLOG | Founder | NOT_TESTED | PUBLISH,COMMERCIAL | project_control/ROADMAP.md | Gates deportivos, visuales y comerciales antes de lanzamiento |
| SP-001 | Sports Data LIVE Day 3-7 | BLOCKED | Datos / Founder | REAL_PRODUCTION_HISTORICAL | EXTERNAL | project_control/domains/SPORTS.md | Conservar DAY 3/4/5; reanudar observacion solo autorizada |
| DATA-001 | Pilot / quota / rights | BLOCKED | Datos | NOT_TESTED | EXTERNAL | project_control/domains/DATA.md | Fuente, permisos, cuota y muestra relevantes verificables |
| AI-001 | SHARK foundation | BACKLOG | SHARK / Datos | LOCAL_ONLY | EXTERNAL | project_control/domains/SHARK.md | Demostrar input real antes de otra inferencia |
| UX-001 | H07 / brand anatomy | BLOCKED | Founder / Creative Director | NOT_CERTIFIED | ART | reports/NEMESIS_OFFICIAL_VISUAL_REFERENCE_ALIGNMENT_REPORT.md | Decision artistica contra las 16 referencias; no nuevo arte automatico |
| UX-002 | App Icon Identity / PR9 | DONE | Codex / QA | INCLUDED_IN_BASE | PUBLISH | project_control/LOCKED_CONTRACTS.md | Preservar assets web; instalacion nativa y produccion actual no recertificadas |
| UX-003 | CX-DESIGN-02 / R8 / R9 | QA | Codex / Creative Director | LOCAL_ONLY | ART,PUBLISH | reports/LOCAL_CONTINUITY_20260919.md | R8 preservado; recomendaciones compactas, Calendario accesible, 45 vistas actuales; R9/H07/conformidad global pendientes |
| QA-002 | CI / preflight / smoke | BACKLOG | Codex / Release | NOT_RUN_CURRENT_CANDIDATE | PUBLISH | project_control/RELEASE_STATE.md | Comprobar revision autorizada; no heredar fallos CI de septiembre 9 |
| QA-001 | Environmental positive cases | BLOCKED | QA / Plataforma | NOT_CERTIFIED | ENV | reports/NEMESIS_OFFICIAL_VISUAL_REFERENCE_ALIGNMENT_REPORT.md | Mantener bloqueos historicos; resolver causa sin skips ni expectativas rebajadas |
| OPS-001 | Sentinel / release gate | DONE | ChatGPT / QA | PASS_LOCAL_SAFE | — | reports/SENTINEL_OPERATIONAL_CLOSURE_20260923.md | Preservar executor local; cada Smoke revalida fronteras; no habilitar executor productivo |
| OPS-002 | Hygiene / organization | IN_PROGRESS | ChatGPT / Founder | REMOTE_RECONCILIATION | LEGACY | project_control/ACTIVE_WORK.md | Reconciliar GitHub actual y extraer trabajo único antes de cerrar supersedidos; conservar UNKNOWN y worktrees |
| OPS-003 | Legacy retirement | BLOCKED | Arquitectura / Founder | NOT_CERTIFIED | LEGACY,MATERIAL | project_control/CONVERSATION_INDEX.md | Cero consumidores, alternativa, pruebas y rollback antes de retirada |
| BIZ-001 | LRM-001 / FIRST10 | BACKLOG | Founder | NOT_TESTED | PUBLISH,COMMERCIAL | project_control/ROADMAP.md | No activar pagos, altas ni mensajes automaticamente |
<!-- queue:end -->

## Correspondencia historica, no otra cola

NEM-01 -> CX-002/OPS-002; NEM-02 -> CX-001/SP-001; NEM-03 -> OPS-001;
NEM-04 -> DATA-001/CX-004; NEM-05/06 -> CX-001/CX-005/CX-006;
NEM-07 -> foundation V944 existente, V946 pendiente de especificacion;
NEM-08 -> Match Context/CX-003; NEM-09 -> UX-001/CX-008;
NEM-10 -> CX-005; NEM-11/LRM-001 -> CX-011/BIZ-001.

Estados del 09/09 desplazados, preservados en Git y fuentes del indice.
No ejecutar una fila por su existencia ni publicar por estar en QA o DONE.
