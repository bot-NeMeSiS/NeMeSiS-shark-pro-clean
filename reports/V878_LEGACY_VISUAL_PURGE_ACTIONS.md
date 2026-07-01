# V878 Legacy Visual Purge Actions

## Acciones realizadas

- Se marco `v869-reference-*` como deprecated bridge mediante `v878-deprecated-visual-class`.
- Se agrego sistema canonico `ns-*`.
- Se corrigieron defaults mojibake en macros de picks/widgets.
- Se unificaron botones generados por macros bajo `ns-button`.
- Se unificaron cards generadas por macros bajo `ns-card`.
- Se unificaron chips/badges generados por macros bajo `ns-chip` y `ns-badge`.

## No eliminado por seguridad

- Bloques CSS antiguos con `!important`.
- Templates historicos activos.
- Motores usados por rutas.
- Navegacion admin/cliente existente.

## Motivo

Borrar a ciegas podria romper rutas activas. V878 neutraliza y documenta legacy antes de una purga destructiva futura.

