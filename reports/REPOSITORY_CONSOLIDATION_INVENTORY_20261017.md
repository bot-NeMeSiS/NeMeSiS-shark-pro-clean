# Inventario de consolidación de NeMeSiS SHARK PRO
Observado: 2026-10-17 16:33:17 +02:00 (hora local del equipo). Lecturas remotas y estado local se separan explícitamente.

## Diagnóstico ejecutivo
- Repositorio oficial recomendado y usado por producción: bot-NeMeSiS/NeMeSiS-shark-pro-clean, público, default branch main.
- main remoto observado: 09e772f51030ddb128b79aeeded247b7857e866c.
- Runtime público consultado por GET a las 16:30:03 Europe/Madrid: HTTP 200, READY, version_files_match=true y git_commit_hint=09e772f51030ddb128b79aeeded247b7857e866c.
- Render tiene un servicio web y un Cron, ambos enlazados al repo oficial y main. El despliegue más reciente reportado por Render para ambos está LIVE en 09e772f51030ddb128b79aeeded247b7857e866c. No se hizo deploy.
- El checkout abierto del Escritorio es una rama de búsqueda en f3fe100a, dos commits detrás de main; conserva tres archivos propios sin seguimiento. No actualizarlo ni cambiar de rama antes de protegerlos y revisar su utilidad.
- El worktree codex/control-center-reliability-20261017 parte del main actual, tiene un commit local exclusivo de mejora de resúmenes de highlights y once archivos modificados/tres? entradas de trabajo P0 más dos informes nuevos. Su lote de pruebas locales pasó 138/138. No hay push, commit del lote P0 ni merge a main.
- GitHub muestra 254 ramas remotas. 133 refs son ancestros directos de main y 121 no lo son; la segunda cifra incluye ramas posiblemente ya integradas por squash, borradores y refs de recuperación, así que no se usa como criterio de eliminación. Ver CSV completo.
- El repositorio local pasa fsck de conectividad (exit 0); Git reportó objetos colgantes históricos. No ejecutar prune/gc durante la consolidación.
- 38 worktrees locales registrados; 14 tienen cambios sin commit. No se eliminó, reseteó ni sobrescribió ninguno. Ver inventario completo CSV.
- Los checkpoints/estados más recientes de la conversación están en otra carpeta de referencia; se leyeron como historial, no como evidencia actual. La lectura actual del runtime reemplaza cualquier hash guardado en esos documentos.

## Repositorios relacionados

| Repositorio | Estado observado | Clasificación | Propuesta |
|---|---|---|---|
| bot-NeMeSiS/NeMeSiS-shark-pro-clean | Único con código de producto; default main; repo enlazado a Web y Cron Render | KEEP — oficial | Mantener como fuente única; main como línea estable |
| bot-NeMeSiS/NeMeSiS-SHARK-PRO- | Repositorio público vacío, 0 ramas, 0 PR | ARCHIVE — propuesto | Archivar cuando confirmes; no borrar |
| bot-NeMeSiS/NeMeSiS-SHARK-PRO | Privado, tamaño GitHub 0, solo ref main y 0 PR; contenido operativo no encontrado | ARCHIVE — propuesto, pendiente confirmar intención | Mantener hasta confirmar que no se usa como respaldo externo |
| bot-NeMeSiS/NEMESIS-SHARK-PRO-ULTIMATE | Privado, tamaño GitHub 0, solo ref main y 0 PR; contenido operativo no encontrado | ARCHIVE — propuesto, pendiente confirmar intención | Mantener hasta confirmar que no se usa como respaldo externo |

No se propone borrar ningún repositorio. El tamaño 0 y la ausencia de README se consideran evidencia limitada; los dos repos privados no se tratan como definitivamente vacíos sin inspección de su árbol completo.

## Render — lectura actual

| Recurso | Repositorio / rama | Estado y versión | Configuración relevante |
|---|---|---|---|
| Web srv-d7t9j2favr4c738hm0i0 | clean / main | LIVE; deploy dep-db7ttejtqb8s73bs7070; SHA 09e772f51030ddb128b79aeeded247b7857e866c; runtime GET READY | Starter, 1 instancia, health /api/health, disco dsk-d7t9j2favr4c738hm0q0 montado /data, 2 GB |
| Cron crn-d8mlmhq8qa3s73e9v2tg | clean / main | LIVE; deploy dep-db7ttejtqb8s73bs7290; mismo SHA 09e772f51030ddb128b79aeeded247b7857e866c | Starter, cada 5 minutos; último éxito reportado 2026-10-17 16:21 Madrid |

El conector de Render no expone uso actual del filesystem del disco ni coste facturado; no se afirma que el disco esté vacío o con espacio suficiente. Último inventario de uso disponible en los registros: 14-oct, histórico. Sin lectura autenticada actual de /data en esta sesión. No se invocó Cron ni backup.

## Ramas y PR — ramas activas o con decisión

| Rama / PR | Estado y aportación | Clasificación propuesta |
|---|---|---|
| main | Deploy activo, runtime idéntico | KEEP — oficial |
| codex/control-center-reliability-20261017 (solo local) | 1 commit local sobre main (resúmenes responsive); modificaciones P0 del Centro de Datos/proveedores, claridad de frescura/cuota/coste y tests | MERGE — candidato revisable, no publicado; mantener intacto |
| codex/search-first-team-candidates (checkout Escritorio) | HEAD f3fe100a; 2 behind, 0 ahead según relación de refs; 3 archivos untracked locales de acceso PC/centro de mando | KEEP — conservar los 3 archivos y el checkout; no parece aportar commit exclusivo a main |
| feat/competition-standings-from-results / #239 | DRAFT, base exacta main; 5 workflows SUCCESS en HEAD observado | MERGE — candidato, requiere revisión final/decisión |
| fix/backup-deadline-diagnostics-current-main / #236 | DRAFT, 5 workflows SUCCESS; base obsoleta f3fe100a | MERGE — candidato técnico tras rebase/comparación; preservar integrity/hash/publicación atómica |
| docs/production-operations-truth-20261014 / #237 | DRAFT, 3 workflows SUCCESS; base obsoleta | MERGE — docs tras revisar vigencia |
| perf/sports-sync-window-query / #233 | DRAFT, 7 workflows SUCCESS; base 0528ad845... | MERGE — candidato tras rebase y medir beneficio |
| perf/pwa-versioned-static-cache / #232 | DRAFT, 7 workflows SUCCESS, mergeable=false | KEEP — resolver conflicto y revisar privacidad de caché |
| codex/backup-deadline-diagnostics / #216 | DRAFT, 7 workflows SUCCESS; base antigua y solape con #236 | ARCHIVE — propuesto solo tras comparar/extractar cualquier cambio exclusivo |
| integration/definitive-product-truth / #198 | DRAFT, base antigua, mergeable=false; umbrella sobre trabajo ya integrado | ARCHIVE — propuesto tras verificar que no guarda cambios únicos |
| fix/production-browser-canonical-contracts / #226 | Cerrada sin merge; reemplazada por #225 merged | ARCHIVE — propuesto, conservar ref hasta verificar reachability |
| feat/free-tier-ad-monetization / #238 | DRAFT; Smoke y Render Deploy Guard fallidos en el HEAD observado; base f3fe100a | KEEP — no integrar hasta corregir y revalidar |
| ci/phase3-main-integration / #202 | DRAFT; 6/7 workflows success, Smoke failed; gate Fase 3 pendiente | KEEP — aislada; no integrar |
| codex/phase3-unified-sports-truth / #187 | DRAFT/no mergeable; Fase 3 no certificada | KEEP — aislada |
| feat/premium-visual-pass / #195 | DRAFT, 6 workflows success, no mergeable, base antigua | KEEP — preservar visuales y reconciliar después |
| feat/sportsdb-broadcast-memory / #194 | DRAFT, 7 workflows success, no mergeable, base antigua | KEEP — revisar permisos/licencias antes de integrar |

PRs #219–#231 y #234–#235 aparecen integradas en main, salvo #226 (cerrada sin merge); #232 y #233 siguen abiertas. Los nombres de PR/ramas en la tabla no sustituyen revisión de diffs.

## Worktrees locales

El CSV lista los 38 worktrees con HEAD, rama, cambios sin commit y diferencia de conteo respecto a origin/main. Los cambios sucios más sensibles a proteger:
- Escritorio codex/search-first-team-candidates: tres archivos nuevos de acceso de PC.
- control-center-audit / codex/control-center-reliability-20261017: modificaciones de P0 y dos informes locales.
- visualizations/.../cx-design-02: 399 entradas modificadas/no rastreadas.
- .tmp_reference_review/design_02_conformance_20260910/release: 302 entradas.
- data/local_dev/admin-master-integration: 26 entradas.
- fix/admin-odds-diagnostics: 9 entradas.
- feature/automatic-broadcast-client-20261004: 9 entradas.
- Otros worktrees con cambios: nemesis-home-agenda-polish, nemesis-sentinel-operaciones, production-truth, combined detached, postmatch-lifecycle, phase3 y phase3-baseline.
No se propone limpiar ningún worktree en esta fase.

## Validación y propuesta de consolidación

1. KEEP como oficial clean/main; no mover ni refrescar el checkout del Escritorio hasta crear una copia verificable de sus tres archivos propios y decidir cómo integrar la funcionalidad local de Centro de Mando.
2. Mantener sin cambios el worktree P0 y presentar su diff como primera PR local. HEAD actual: f80c18c3fc809b3e17c4b2e63f54d37ebebe0dc7, padre main 09e772f5. Lote P0: 138 PASS en pruebas de seguridad, estado proveedor, frescura deportiva, membresías, ruta admin, PC/móvil y resúmenes. git diff --check limpio. El primer intento se ejecutó desde el directorio equivocado; repetido desde el worktree correcto y con Chrome local, pasó. No alterar esa evidencia ni afirmar pruebas globales.
3. Revisar #236 vs #216 y seleccionar un solo candidato de diagnóstico de backup; rebasar #236 a main solo en rama de trabajo, volver a correr sus pruebas y comparar instrumentación. Nada demuestra todavía causa raíz del TIMEOUT de producción.
4. Revisar #233, #232, #239 y #237 individualmente sobre main actual; preservar #238, #202, #187, #194, #195 y #198 hasta extraer y clasificar cambios únicos.
5. Eliminar duplicación de repositorios solo mediante archivar los tres placeholders cuando autorices. Para ramas: primero preservar/quitar los merges históricos del mapa; revisar aparte los 121 tips que no son ancestros. DELETE PROPOSED: ninguno.
6. Después de aprobar el inventario: preparar una rama de consolidación nueva desde main, integrar solo diffs seleccionados con pruebas enfocadas y CI; publicar un PR para revisión. El merge a main, push, deploy, cierre/archivo y borrado siguen sin ejecutarse sin autorización expresa separada.

## Archivos de evidencia
- Inventario completo de refs remotas: reports/REPOSITORY_BRANCHES_20261017.csv
- Worktrees locales: reports/REPOSITORY_WORKTREES_20261017.csv
- Comparativa local P0: reports/INTEGRATION_SERVICES_P0_20261017.md
- Lectura de servicios de integraciones: reports/INTEGRATION_SERVICES_LIVE_READ_20261017_1611.json
- No se creó commit ni se modificó configuración de GitHub/Render.
