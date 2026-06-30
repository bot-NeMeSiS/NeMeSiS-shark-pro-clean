# V871 Screen Visual Confirmation QA

## Probado local con navegador
- Captura desktop `/`: `reports/V871_desktop_home.png`.
- Captura desktop `/app`: `reports/V871_desktop_app.png` con redirección esperada a login si no hay sesión cliente.
- Captura móvil `/picks`: `reports/V871_mobile_picks.png`.
- Captura móvil `/live`: `reports/V871_mobile_live.png`.
- Captura móvil `/shark`: `reports/V871_mobile_shark.png`.

## Métricas de scroll horizontal
- `/` desktop 1280x800: sin overflow horizontal.
- `/app` desktop 1280x800: sin overflow horizontal; sin sesión redirige a `/cliente-login`.
- `/picks` móvil 390x844: sin overflow horizontal.
- `/live` móvil 390x844: sin overflow horizontal.
- `/shark` móvil 390x844: sin overflow horizontal.

## Botones repetidos
No se detectaron textos repetidos visibles tipo `Partidos Partidos`, `Picks Picks`, `SHARK SHARK`, `Telegram Telegram`, `Panel Panel` o `Datos Datos` en las rutas capturadas.

## No probado
- No se probó Render real.
- No se probaron pagos reales.
- No se enviaron Telegram reales.
- No se declara pixel-perfect.
