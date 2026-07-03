# V885 Client Sidebar Design Decision

## Regla final

- Cliente desktop: sidebar lateral premium.
- Cliente movil: bottom nav compacta.
- Admin: rail admin propio.
- SHARK flotante: solo cliente, nunca admin, nunca duplicado.

## Sidebar cliente desktop

- Clase canonica: `ns-client-sidebar`.
- Zona: `data-nav-zone="client-sidebar"`.
- Posicion: izquierda, fija, compacta, sin tapar contenido.
- Rutas: Inicio, Partidos, Live, Picks, SHARK, Telegram, Perfil, Track Record, Soporte y Salir.
- Ruta activa: clase `is-active` desde Jinja y JS.

## Movil

- `ns-client-sidebar` queda oculto.
- `bottom-nav-clean[data-nav-zone="client-bottom"]` queda como fuente unica.
- Maximo 5 accesos principales.

## Admin

- `v808-admin-rail` sigue como fuente admin.
- `ns-client-sidebar`, bottom nav cliente y floating SHARK quedan ocultos en `.ns-admin`.
