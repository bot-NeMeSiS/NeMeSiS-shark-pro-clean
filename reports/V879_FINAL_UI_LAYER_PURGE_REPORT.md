# V879 Final UI Layer Purge Report

## Decisión

V879 no borra CSS legacy a ciegas. El sistema único activo es `ns-*`, y las clases antiguas quedan controladas por compatibilidad.

## Corregido

- Se añade bloque V879 final sobre `body[data-v879-shell="true"]`.
- Se compactan cards, tablas, empty states, heroes y acciones.
- Se evita mezcla visual cliente/admin con reglas específicas.
- Se mantiene `v878-deprecated-visual-class` solo como puente en partials.

## Pendiente V880

- Browser QA real.
- Listado de macros `reference_*` todavía usadas.
- Retirada física de clases legacy solo después de capturas y Sentinel limpio.
