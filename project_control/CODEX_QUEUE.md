# Codex Queue

Unica cola ejecutable; no otorga permisos. Codex integra y prueba, Founder decide.
IDs nuevos: SP-###, DATA-###, AI-###, UX-###, QA-###, OPS-###, BIZ-###, CX-###.
Los aliases CX-* y NEM-* se conservan, no representan tareas duplicadas.

Estados: BACKLOG, READY, IN_PROGRESS, BLOCKED, QA, PRODUCTION_VALIDATION, DONE, WONT_DO.
Evidencia: REAL_PRODUCTION, LOCAL_ONLY, NOT_TESTED, LOCAL_SAFE_BLOCKED.
WAITING solicitado se representa BLOCKED con dependencia explicita, no noveno estado.
DONE siempre indica alcance/evidencia; DONE local no significa publicado.

| ID | Alias acordado | Estado | Evidencia | Alcance y siguiente accion |
|---|---|---|---|---|
| CX-001 | CX-SE-01 / COORD-8-SE-01 R1 | DONE | LOCAL_ONLY | PASS_LOCAL_SCOPE; preservarlo. Suite global PARCIAL, 12 positivos no certificados |
| CX-002 | CX-ORG-01 | QA | LOCAL_ONLY | Control e higiene conocidos implementados; revisar limite truncado y cierre. No otro desarrollo |
| CX-003 | CX-RESULTS-01 / COORD-8-RESULTS-01 R1 | BLOCKED | NOT_TESTED | Espera revision CX-002 y encargo. Extender Calendario/Partidos existentes, no Track Record |
| CX-004 | CX-DATA-01 | BACKLOG | NOT_TESTED | Almacenes/adaptadores ya existen; falta piloto real autorizado y cobertura, no nuevo motor |
| CX-005 | CX-INTELLIGENCE-01 | BACKLOG | NOT_TESTED | Match Context/relato factual ya implementados; siguiente incremento solo ante gap demostrado |
| CX-006 | CX-SHARK-01 | BACKLOG | NOT_TESTED | Reutilizar SHARK/contexto existente; falta evidencia deportiva suficiente, no chatbot nuevo |
| CX-007 | CX-MEDIA-01 | BACKLOG | NOT_TESTED | Media Rights ya implementado; videos/fotos autorizados necesitan evidencia de derechos |
| CX-008 | CX-PLANS-01 | BACKLOG | NOT_TESTED | Membresias/permisos existentes; no recrear tiers ni cambiar precios |
| CX-009 | CX-ANALYTICS-01 | BACKLOG | NOT_TESTED | Growth/Revenue existentes; metrica real y definicion, no numeros inventados |
| CX-010 | CX-STRIPE-01 | BACKLOG | NOT_TESTED | Integracion existente; test aislado/activacion requieren alcance y autorizacion propios |
| CX-011 | CX-FIRST10-01 | BACKLOG | NOT_TESTED | LRM-001/comercial controlado; gates de roadmap, sin alta/cobro/envio automatico |

## Trabajo subordinado, no nuevas sesiones

| ID | Estado | Responsable | Evidencia | Dependencia / aceptacion |
| SP-001 | QA | Datos / Founder | REAL_PRODUCTION | Gate DAY 1-5 en curso; muestra LIVE S/A independiente coherente, sin reinicio |
| DATA-001 | BLOCKED | Datos | NOT_TESTED | Extracto autorizado, plan/cuota/derechos verificables; max piloto acordado, no compras |
| AI-001 | BACKLOG | SHARK / Datos | LOCAL_ONLY | Hechos normalizados ya presentes; demostrar input real antes de otra inferencia |
| UX-001 | BLOCKED | Founder | NOT_TESTED | Decision artistica SHARK/fondo; no automated override |
| UX-002 | BLOCKED | Codex / Release | LOCAL_ONLY | App icons implementados, cdd88e50 en PR #9; 139/139 focales. Produccion bloqueada por preflight/smoke previos; no bypass ni otra capacidad |
| UX-003 | DONE | Codex / QA | LOCAL_ONLY | Creative & Design formalizado en ejecutores existentes; 16 referencias, 7 roles y Founder. No aprobacion visual ni despliegue |
| QA-002 | BLOCKED | Codex / Release | LOCAL_ONLY | Smoke: dependencia corregida sin commit; V944: falta evidencia real generada en CI. 623 tests: 611 PASS, 12 LOCAL_SAFE_BLOCKED. Revisar antes de continuar |
| QA-001 | BLOCKED | QA / Plataforma | LOCAL_SAFE_BLOCKED | 12 positivos de SE; arnes heredable, PID exclusivo, sin quitar LOCAL SAFE |
| OPS-001 | BLOCKED | Release / Founder | NOT_TESTED | Autorizacion candidato, rama + PR + checks, luego Sentinel SHA efectivo |
| OPS-002 | QA | Codex | LOCAL_ONLY | Higiene CX: referencias/ignore/retirada cache y huellas, sin codigo funcional |
| OPS-003 | BLOCKED | Arquitectura / Founder | NOT_TESTED | Retirada legacy adicional: especificacion completa y consumidor/alternativa demostrados |
| BIZ-001 | BACKLOG | Founder | NOT_TESTED | FIRST 10 tras gates deportivos, calidad, operacion y permisos comerciales |

## Correspondencia historica

NEM-01 -> CX-002/OPS-002; NEM-02 -> CX-001/SP-001; NEM-03 -> OPS-001;
NEM-04 -> DATA-001/CX-004; NEM-05/06 -> CX-001 y siguientes incrementos CX-005/006;
NEM-07 -> preservacion de foundation V944 y especificacion V946 aun no recuperada;
NEM-08 -> Match Context existente, CX-003 solo resultados pendientes;
NEM-09 -> UX-001/CX-008; NEM-10 -> CX-005 BACKLOG, no bucle activado;
NEM-11/LRM-001 -> CX-011/BIZ-001. No cerrar V946 por su numero ni borrar su pendiente.

Prioridad de trabajo != severidad de incidente. Nunca arrancar la fila siguiente
solo porque exista en esta tabla; respetar autorizacion y dependencias.
