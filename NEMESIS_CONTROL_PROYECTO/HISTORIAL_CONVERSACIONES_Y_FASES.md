# Historial de Conversaciones y Fases

## Linea reciente verificable en Git

| Fecha Madrid | Commit | Fase demostrada |
|---|---|---|
| 2026-09-01 | `3fbc14cd` | Superficies de inteligencia de partido |
| 2026-09-01 | `80a1e813` | Continuidad de datos de proveedor real |
| 2026-09-01 | `0d20bf0d` | Commit accidental de artefactos QA/runtime |
| 2026-09-01 | `b944a7b7` | Revert trazable del commit accidental |
| 2026-09-01 | `eb698296` | Reconciliacion de LIVE cacheado |
| 2026-09-01 | `001632d0` | Persistencia de evidencia del pipeline |
| 2026-09-01 | `30d85478` | Evidencia de proveedor en respuesta cron |
| 2026-09-01 | `e6dfc308` | Identidad de fixture auditada |
| 2026-09-01 | `c2c0574b` | Limites del plan gratuito API-Football |
| 2026-09-02 | `670ef8df` | Commit existente; mensaje no descriptivo |
| 2026-09-04 | `fddbeea3` | Hotfix fail-closed para LIVE obsoleto |

## Fases acumuladas

1. Producto cliente y centros deportivos.
2. Admin/Founder, Growth, Revenue y Operations.
3. Local Safe, Mobile LAN y controles de seguridad.
4. Continuous Evolution, Product Memory y master scheduler.
5. Consolidacion visual y QA de referencias.
6. Sports P0: terminal nunca LIVE, relevancia deportiva e identidad de competicion.
7. Sports Knowledge: Match, Team, Competition, Player, eventos, stats y media rights.
8. Correccion DAY 2: lecturas stale excluidas del LIVE publico.
9. Fase actual: una sola Sports Truth para todos los adaptadores y documentacion canonica.

## V944 y V946 reconciliadas

| Fase | Fuente recuperada | Implementacion actual | Estado |
|---|---|---|---|
| V944 Match Center Foundation | `MATCH_CENTER_FOUNDATION_REPORT.md`, Decision Report y backlog | Commit de incorporacion `b6fc366d`; `MatchContext`, ruta, componentes, tests y Sentinel presentes; ampliaciones posteriores agregaron timeline, lineups, stats, H2H y standings condicionales; Browser QA local actual 6/6 | IMPLEMENTADO_EN_MAIN_Y_AMPLIADO |
| V946 | Sin prompt, documento, archivo, test, texto o commit identificable | `git log --all -S V946` y busqueda del arbol sin resultados | BLOQUEADO_ESPECIFICACION_NO_RECUPERABLE |

El informe antiguo `docs/NEMESIS_RECONCILIATION_AUDIT.md` que dejaba V944 sin
verificar fue superado por `b6fc366d` y por el estado actual. La trazabilidad
documental original de V944 no esta concentrada en una sola especificacion, pero
la implementacion es comprobable. V946 no se deduce por numeracion.

## PR documental #7

- Head recuperado en solo lectura: `ad297cf56b7ab302a86b16ae261634549c5a68a4`.
- El rango desde `fddbeea3` contiene 21 commits documentales y su resultado neto
  aporta siete documentos de control; las siete copias locales actuales
  tienen contenido diferente y mas reciente.
- El PR no incluye `MAPA_COMPLETO_ECOSISTEMA_NEMESIS.md` ni evidencia V946.
- No se fusiono, cerro, modifico ni uso para sobrescribir la documentacion local.

## Conversaciones verificadas

Se leyo contenido acotado de C20, C19, C18, C17, C16, C14, C13 y C03 para
confirmar tema antes de proponer nombres. El mapa detallado con IDs permanece
privado y fuera del repositorio. La interfaz disponible no permite renombrar
chats de ChatGPT; solo se renombro y verifico la tarea Codex C21.

## Regla de interpretacion

Un commit anterior puede aportar historia, pero el comportamiento vigente se determina por HEAD, pruebas actuales y runtime servido. Ningun informe historico sustituye evidencia del codigo actual.
