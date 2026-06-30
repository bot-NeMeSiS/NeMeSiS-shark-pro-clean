# V868 Cliente móvil Visual QA

Objetivo móvil: sensación de app nativa, sin scroll horizontal y con acciones claras.

Mejoras aplicadas:

- `overflow-x` protegido en `html/body`.
- Contenedores principales limitados a `100vw`.
- Filtros y acciones convertidos en carriles horizontales internos controlados.
- Cards de picks/live/Sentinel compactadas.
- Bottom nav con ancho máximo protegido.
- SHARK flotante elevado sobre la navegación inferior.

Validación con navegador local:

- Viewport usado: 390x844.
- Capturas guardadas: `reports/V868_mobile_home.png`, `reports/V868_mobile_app.png`, `reports/V868_mobile_picks.png`, `reports/V868_mobile_live.png`, `reports/V868_mobile_shark.png`, `reports/V868_mobile_telegram.png`, `reports/V868_mobile_admin_dashboard.png`, `reports/V868_mobile_admin_continuous-sentinel.png`.
- `/app` y `/telegram` redirigieron a login por no haber sesión local; se verificó igualmente que no provocan scroll horizontal.
- Admin redirigió a `/admin-login` por protección correcta sin sesión admin; no se afirma captura de panel admin autenticado.
- Resultado medido: `overflowX=false` en todas las rutas capturadas.
