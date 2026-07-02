# V884 Preflight - Client/Admin Functional Flow

Version objetivo: V884_CLIENT_ADMIN_FUNCTIONAL_FLOW_AND_SCREEN_EXPERIENCE_FINAL

## Base local

- Carpeta oficial: C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro
- VERSION.txt local: V884_CLIENT_ADMIN_FUNCTIONAL_FLOW_AND_SCREEN_EXPERIENCE_FINAL
- APP_VERSION local: V884_CLIENT_ADMIN_FUNCTIONAL_FLOW_AND_SCREEN_EXPERIENCE_FINAL
- Base funcional preservada: V878 sistema ns-*, V881 navegacion, V882 core product recovery, V883 Visual Company Worker y V884 worker/matches QA previo.

## Produccion Render

- Endpoint revisado: https://bot-apuestas-crgf.onrender.com/api/runtime-version
- Produccion real sigue sirviendo: V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL
- Estado: BLOCKER de despliegue. No se declara V884 en Render.

## Guardrails

- No se uso ZIP viejo V827.
- No se trabajo en carpeta anidada.
- No se tocaron secretos.
- No se envio Telegram real.
- No se tocaron pagos reales.
- No se inventaron partidos, picks, cuotas, resultados ni escudos.

## Preflight tecnico

- Runtime local expone flag V884 funcional.
- base.html mantiene data-v884-shell.
- app.css usa cache busting V884.
- Visual Company Worker existe y queda reforzado para flujo funcional.
- Continuous Sentinel mantiene reglas previas y suma reglas V884 de botones/rutas/estados.
