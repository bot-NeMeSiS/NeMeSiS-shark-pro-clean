# NeMeSiS - Master Control

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
