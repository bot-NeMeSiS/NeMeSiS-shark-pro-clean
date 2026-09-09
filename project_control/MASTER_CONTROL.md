# NeMeSiS - Master Control

Entrada operativa unica. Actualizacion: 2026-09-09, reconciliacion UX-002/UX-003/QA-002.
DEPORTE PRIMERO -> SHARK DESPUES -> APUESTAS EN TERCER LUGAR.

## Ahora

| Identidad | Valor | Alcance |
|---|---|---|
| PRODUCTION_SHA | `c6eaa003e6ae0e9d4af7d98198ec6eefafc97b04` | Ultimo observado DAY 5, 2026-09-08 22:37:56 Madrid; no verificado hoy |
| GITHUB_SHA | `c6eaa003e6ae0e9d4af7d98198ec6eefafc97b04` | main consultado por conector read-only 2026-09-09 |
| LOCAL_SHA | `6858aedbbd04211500028b7aaf56c3f5980f833d` | codex/app-icon-identity, mismo HEAD remoto de rama; Creative/CI adicionales sin commit |

SE-01/CX y DAY 3/4/5 llegaron a la rama en el commit externo 6858aedb, NO a main.
El commit de iconos cdd88e50 es su padre; PR #9 abierta, merged=false. El estado
completo, alcance y fuentes viven en [CURRENT_TRUTH](CURRENT_TRUTH.md).

## Decision de calidad

- SE-01 = **PASS_LOCAL_SCOPE / DONE**. PRODUCT_REGRESSIONS abiertas = 0,
  UNKNOWN diagnosticos = 0, UNEXPLAINED_FAILURES = 0, CLEANUP_FINAL_ERRORS = 0.
- Suite global SE-01 = **PARCIAL: 543 PASS + 12 LOCAL_SAFE_BLOCKED / NOT_CERTIFIED,
  0 errors**, 555 tests. Nunca reetiquetar esta ejecucion como PASS global.
- Focal SE-01 28/28; grupo focal 30/30. Procedencia RESOLVED LOCAL.
- P0/P1 globales de produccion: no recertificados hoy. No heredar un cero antiguo.
- Sports real = IN_PROGRESS; DAY 3/4/5 protegidos; LIVE real aun no certificado.
- Visual SHARK/fondo: decision humana pendiente; no redisenar en CX-ORG-01.

## Operacion y siguiente trabajo

- Ultimo encargo: **reconciliacion Creative & Design / iconos / CI**. Formalizacion
  PASS_LOCAL; publicacion BLOCKED en PR #9. Resumen unico en
  [Producto/Visual](domains/PRODUCT_VISUAL.md#reconciliacion-ux-002--ux-003--qa-002).
  qa remoto SUCCESS; smoke/preflight FAILURE. Dependencias smoke corregidas solo
  localmente; V944 sigue sin evidencia requerida. No bypass ni Actions nuevas.
  Suite nueva 623: 611 PASS, mismos 12 LOCAL_SAFE_BLOCKED, 0 errors; PARCIAL.
  CX-ORG-01 conserva su cierre QA pendiente de revision; ver [ACTIVE_WORK](ACTIVE_WORK.md).
- Siguiente elegible: **CX-RESULTS-01**, BLOQUEADO hasta revision de CX; no iniciado.
- Cola unica e IDs anteriores: [CODEX_QUEUE](CODEX_QUEUE.md).
- FIRST 10 y gates: [ROADMAP](ROADMAP.md); no comercializacion automatica.
- Workers: ocho roles registrados y 34 modulos de workforce, no 34 agentes activos.
  Creative & Design agrega siete responsabilidades a ejecutores existentes,
  cero procesos nuevos; no certifica fidelidad ni aprueba la marca.
  Ejecucion autonoma actual NOT_TESTED. Detalle en [QUALITY](domains/QUALITY.md).
- Master Scheduler/telegram-auto-tick/Continuous Evolution: preservados;
  ACTIVE actual no recertificado. AUTO-01 sigue BLOQUEADO_ACTIVACION.
  Ver [PLATFORM](domains/PLATFORM.md). No crear otro scheduler.
- GitHub issue #8 es coordinacion, no autorizacion automatica de publicacion.

## Autoridad y lectura

1. REAL PRODUCTION, con SHA, instante y alcance de observacion.
2. GITHUB MAIN, version disponible, no comportamiento probado.
3. OFFICIAL CODEX WORKTREE, con diff y huella; puede contener LOCAL_ONLY.
4. CANONICAL REPORTS, evidencia fechada del arbol que realmente probaron.
5. PROJECT_CONTROL, sintesis operativa subordinada a esas evidencias.
6. CHAT HISTORY, contexto y autorizaciones explicitas, no prueba de ejecucion.

La jerarquia describe hechos; produccion no autoriza acciones ni modifica permisos.
Una fuente antigua conserva su fecha y no prevalece sobre observacion nueva.
Si falta acceso, registrar NOT_TESTED; nunca completar un SHA/resultado por inferencia.

[Contratos bloqueados](LOCKED_CONTRACTS.md) | [Sports](domains/SPORTS.md) |
[Datos](domains/DATA.md) | [SHARK](domains/SHARK.md) |
[Producto/Visual](domains/PRODUCT_VISUAL.md) | [Calidad](domains/QUALITY.md) |
[Plataforma](domains/PLATFORM.md) | [Negocio](domains/BUSINESS.md).

NEMESIS_CONTROL_PROYECTO queda como continuidad historica con referencias aqui;
NEMESIS_DOCUMENTACION conserva sus 14 indices; reports conserva evidencia tecnica.
Las biblias/vision congeladas siguen protegidas, sin convertirse en backlog aprobado.
