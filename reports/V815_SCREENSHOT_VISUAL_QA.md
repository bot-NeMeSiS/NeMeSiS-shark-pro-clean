# V815 Screenshot Visual QA

## Estado

No se pudieron generar screenshots reales en este entorno.

## Motivo

No hay herramienta de navegador directa disponible en esta sesion. Se intento comprobar Playwright mediante Node REPL, pero el kernel no pudo arrancar por restriccion de sandbox de Windows.

## Validacion alternativa realizada

- Smoke test Flask local de rutas cliente/admin sin errores 500.
- Parseo Jinja de 143 templates sin errores.
- Checks V815 de runtime, visual shell y rutas.
- `/api/runtime-version` devuelve V815 y `has_v815_shell=true`.
- HTML base contiene meta V815, comentario fuente V815 y `data-v815-shell=true`.
- CSS V815 contiene capa activa y cache-busting.

## Recomendacion en Render

Despues de desplegar, abrir:

- `/api/runtime-version`
- `/app`
- `/calendar`
- `/live`
- `/picks`

Y verificar en codigo fuente:

- `NEMESIS V815 CLIENT SHELL ACTIVE`
- `data-v815-shell="true"`
- `app.css?v=V815_RENDER_VISIBLE_CLIENT_ADMIN_REFERENCE_REBUILD_CERTIFIED`
