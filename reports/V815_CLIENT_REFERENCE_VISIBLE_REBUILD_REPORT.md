# V815 Client Reference Visible Rebuild Report

## Objetivo

Hacer que V815 sea visible, medible y comprobable en runtime, no solo una capa estetica acumulada.

## Cambios aplicados

- `base.html` ahora incluye marca V815 en meta, body y comentario fuente.
- `app.css` carga con cache-busting V815.
- Se anadio tiburon decorativo V815 solo para cliente.
- Se marco cada template cliente real con `data-v815-template`.
- Se anadio capa visual V815 activada por `data-v815-shell`.
- Se reforzo ocultacion del SHARK flotante en `/shark`.
- Se mantuvo admin sin tiburon decorativo grande.

## Pantallas cliente tocadas

- `home.html`
- `client_app_center.html`
- `calendar.html`
- `live.html`
- `picks.html`
- `match_detail.html`
- `shark.html`
- `profile.html`
- `telegram.html`

## Resultado visual esperado

- Fondo oscuro premium con grid suave.
- Topbar de cristal compacta.
- Tiburon decorativo grande en cliente.
- Cards con borde cyan y mayor profundidad.
- Hero y paneles principales mas visibles.
- Bottom nav movil con aspecto app.
- Un solo boton SHARK flotante.

## No se ha cambiado

- Render config.
- `DB_PATH`.
- Cron/Telegram.
- Membresias.
- Sesiones.
- Pagos.
- SHARK/Auto Picks logic.
