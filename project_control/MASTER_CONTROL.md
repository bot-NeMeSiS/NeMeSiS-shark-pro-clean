# NeMeSiS - Master Control

## Entrada vigente - 2026-09-23

Leer `CURRENT_TRUTH.md` para identidad comprobada, `ACTIVE_WORK.md` para alcance y
`CODEX_QUEUE.md` para la unica cola. Mision OPS-002/CX-002: higiene LOCAL_ONLY;
informe unico actualizado: `GIT_RELEASE_CLEANUP_REPORT.md` en la raiz.
Main remoto comprobado `706094630d337f9e329a8401fae217b316a9b49c`; produccion no
reobservada aqui. PR72/60/68 preservadas; no commit, push, merge ni deploy.
Las declaraciones de las secciones anteriores por fecha son evidencia historica,
no autoridad sobre Git o runtime actuales ni autorizacion para ejecutar trabajos.

## Historico: verdad operativa remota · 2026-09-20

Esta sección es la entrada autoritativa para continuar trabajo remoto. Las secciones
locales del 2026-09-19 que siguen debajo se preservan como historia y evidencia; ya
no describen el estado actual de GitHub/Render.

- Repositorio canónico: `bot-NeMeSiS/NeMeSiS-shark-pro-clean`.
- Baseline remoto verificado antes del candidato STALE: `main@c7237c4669f7f5c5e0ceefe4150fd71039b49507`. Tras cualquier merge, el SHA vigente debe resolverse desde GitHub `main` y confirmarse contra Render exact-SHA; no se infiere desde este documento.
- Render Web `nemesissharkpro`: LIVE en ese SHA.
- Render Cron `telegram-auto-tick`: LIVE en ese SHA, horario `*/5 * * * *`.
- PR #48: frescura canónica por timestamps de entidad.
- PR #50: Founder OS operativo PC/móvil, obligaciones, inbox y Web Push foundation.
- PR #51: fail-fast sistémico de The Odds API, contrato normal preservado; QA,
  preflight y Smoke verdes; producción posterior sin errores/5xx.
- PR #52: Founder OS consume `data_freshness` persistida con 0 llamadas nuevas a
  proveedores; QA, preflight y Smoke verdes; Web/Cron LIVE.
- Observación real del cron 2026-09-20 22:50 Madrid: overall PASS,
  web_readiness PASS, `SPORTSDB_FALLBACK` 180 partidos, API-Football 0 llamadas
  actuales por backoff, Odds `CACHE_REUSED` con 0 llamadas; frescura
  `PARTIAL` sobre 200 filas: 18 FRESH, 179 OBSERVED, 3 STALE, 0 sin reloj.
- El fail-fast de #51 está certificado por pruebas; esa ronda real no lo ejercitó
  porque Odds reutilizó caché, por lo que no se afirma un 429 real post-deploy.
- Trabajo activo: convertir los 3 STALE en evidencia accionable, limitada y
  secret-safe (partido/proveedor/reloj/antigüedad/motivo), sin llamadas externas.
- Regla de despliegue: GitHub `main` + Render Auto Deploy; no disparar deploys
  manuales duplicados.

DEPORTE PRIMERO -> SHARK DESPUES -> APUESTAS EN TERCER LUGAR.

## Historial local preservado · 2026-09-19


Entrada operativa unica. Actualizado 2026-09-19, candidato LOCAL_ONLY.
DEPORTE PRIMERO -> SHARK DESPUES -> APUESTAS EN TERCER LUGAR.

## Leer solo lo necesario

- [Verdad actual](CURRENT_TRUTH.md): hechos, revision y limites.
- [Trabajo activo](ACTIVE_WORK.md): cierre en curso, no otra cola.
- [Cola unica](CODEX_QUEUE.md): un registro por ID; estado, responsable, dependencia y siguiente paso.
- [Decisiones](DECISIONS.md) y [contratos protegidos](LOCKED_CONTRACTS.md): reglas vigentes.
- [Bloqueos](BLOCKERS.md): condiciones, no incidencias cerradas por un documento.
- [Candidatos y publicacion](RELEASE_STATE.md): version y alcance por candidato.
- [Indice de conversaciones](CONVERSATION_INDEX.md): conocimiento recuperable, fuentes y arquitectura documental.
- [Roadmap](ROADMAP.md): estrategia subordinada a la cola, no autorizacion.
- [Dominios](domains/QUALITY.md): especificaciones de consulta; sus estados fechados no sustituyen la verdad actual.

## Autoridad

Produccion observada con SHA/fecha/alcance -> GitHub comprobado -> codigo local y
pruebas de su revision -> informes fechados -> sintesis operativa -> historia.
La jerarquia acredita hechos, nunca amplifica permisos. Un archivo presente no
certifica su contenido; HEAD no identifica cambios sin commit.

Solo desarrollo local en Sentinel. Main limpio en la observacion local; Design
preservado. Sin staging/commit/push/PR/merge/deploy, DB real, proveedores ni pagos.
Sentinel muestra esta informacion en lectura; no ejecuta texto de documentos.

## Continuidad sin duplicaciones

Ultimo cierre: preview reproducible en 54910 y replay final 5-0, cinco superficies.
380 casos distintos comprobados mediante seleccion pertinente y retest afectado;
45 vistas finales. No suite global ni produccion certificadas. Motor Sentinel
conservado; su runner local tiene inicio/parada/reuso. R8, SHARK, membresias y
trabajo anterior preservados. Dos defectos de precedencia/final corregidos.
Main/Design preservados. Siguiente paso: revisar el candidato exacto, sin staging
ni publicacion automatica. La primera carga /app y los bloqueos externos siguen abiertos.

El [cierre funcional local](../reports/LOCAL_CONTINUITY_20260919.md) conserva
resultados y evidencias. Los estados anteriores del 09/09 se recuperan en Git
en c4a81003 y en NEMESIS_CONTROL_PROYECTO; ya no son el encabezado operativo.
No se han movido ni borrado fuentes historicas. No se marca un frente DONE
por organizarlo ni se inicia automaticamente el siguiente.
