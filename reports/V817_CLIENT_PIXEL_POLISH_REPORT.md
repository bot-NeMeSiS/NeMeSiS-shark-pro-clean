# V817 Client Pixel Polish Report

## Cambios aplicados

- `base.html` ahora expone V817 con meta, comentario fuente, cache-busting y `data-v817-shell`.
- Pantallas reales marcadas con `data-v817-template`: home, login cliente, app, calendario, live, picks, detalle de partido, SHARK, perfil y Telegram.
- Se anadio una capa visual final V817 con fondo oscuro profundo, textura suave, tarjetas con mas profundidad, navegacion compacta, botones mas claros y tiburon decorativo con mas presencia.
- `/app`, `/calendar`, `/partidos`, `/live`, `/picks`, `/match/<id>`, `/shark`, `/profile` y `/telegram` reciben estilos especificos por pantalla.

## Garantias

- No se inventan partidos, cuotas, picks, resultados, minutos, ataques ni ROI.
- La capa V817 solo cambia presentacion y preserva V816 como compatibilidad heredada.

## Templates reales tocados

- `templates/base.html`
- `templates/home.html`
- `templates/client_login.html`
- `templates/client_app_center.html`
- `templates/calendar.html`
- `templates/live.html`
- `templates/picks.html`
- `templates/match_detail.html`
- `templates/shark.html`
- `templates/profile.html`
- `templates/telegram.html`
- `static/app.css`
