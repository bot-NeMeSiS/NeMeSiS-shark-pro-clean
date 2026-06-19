# V816 Video vs Reference Visual Gap Report

## Lo visto en el video

- La home seguia percibiendose plana.
- Topbar y tarjetas no transmitian suficiente producto premium.
- KPIs con ceros podian ocupar demasiado protagonismo.
- Calendario y live necesitaban mas aspecto de app deportiva.
- El tiburon decorativo no dominaba visualmente lo suficiente.
- La experiencia parecia depender de CSS/cache y no de runtime certificado.
- Se observo un 502 al final, compatible con deploy/restart, timeout o ruta pesada.

## Lo que muestran las referencias

- Fondo oscuro con mas profundidad.
- Topbar/menú de app premium.
- Cards con jerarquia y sombras.
- Modulos compactos.
- Equipos, escudos, marcadores y estados como protagonistas.
- Mobile con sensacion de app nativa.
- Admin tipo command center.

## Cambios aplicados

- V816 runtime visible: meta, comentario fuente, `data-v816-shell` y cache-busting.
- Capa CSS V816 activa por `data-v816-shell`.
- Templates reales marcados con `data-v816-template`.
- Login cliente incluido en el sistema visual V816.
- Cliente con fondo mas profundo, topbar reforzada, tiburon decorativo mas visible, cards mas premium y bottom nav movil.
- Admin mantiene command center sin tiburon gigante.

## Pantallas reconstruidas o reforzadas

- `/`
- `/cliente-login`
- `/app`
- `/calendar`
- `/partidos`
- `/live`
- `/picks`
- `/match/<id>`
- `/shark`
- `/telegram`
- `/profile`
