# V819 Client Reference UI Rebuild Report

## Cambios cliente

- Shell cliente activada con `data-v819-shell="true"`.
- Pantallas cliente principales marcadas con `v819-certified-screen`.
- Cards, paneles, filas de partido y picks reciben una capa visual consistente.
- Topbar cliente se mantiene unica.
- Bottom nav movil se mantiene unica.
- Soporte queda visible desde la navegacion cliente.
- Iconos corruptos heredados se neutralizan visualmente.
- SHARK flotante se conserva como identidad, pero se oculta en `/shark` para evitar duplicado.

## Plantillas tocadas

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

## Resultado

La experiencia cliente queda menos cargada, con menos duplicidad visual y mas cercana a una app deportiva premium.
