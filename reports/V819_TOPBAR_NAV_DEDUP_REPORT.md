# V819 Topbar Nav Dedup Report

## Duplicados detectados

- Topbar cliente + acciones rapidas cliente V811/V812.
- Topbar + pastillas de sesion V797.
- Bottom nav admin duplicando accesos del rail.
- SHARK flotante en pantalla SHARK.
- Rails cliente heredados de varias versiones.

## Correcciones

- Topbar admin compactada.
- Enlace cliente heredado `Todo` sustituido por `Soporte`.
- Reglas V819 ocultan `v811-top-actions`, `v812-top-actions`, `v797-session-pills`, rails antiguos y dock admin.
- Reglas V819 ocultan bottom nav en rol admin.
- Reglas V819 eliminan iconos corruptos generados por pseudoelementos.

## Navegacion definitiva

- Cliente desktop: topbar unica con Inicio, Partidos, Directo, Picks, SHARK, Cuenta, Soporte y Salir.
- Cliente movil: bottom nav unica con Inicio, Partidos, Directo, Picks y SHARK.
- Admin: topbar compacta y rail/centros admin separados del cliente.
