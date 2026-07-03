# DAILY COMPANY RUN 2026-07-03 - NEXT ACTIONS

## Probado en real

- Endpoint Render real `/api/runtime-version`.
- Produccion responde, pero sirve `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL`.

## Probado local

- Runtime local V885.
- Continuous Sentinel: 10.0, 0 issues.
- Smoke Flask rutas: 29 rutas, 0 fallos.
- Checks V881, V882, V883, V884, V885.
- Madrid Time.
- Jinja parse.
- ZIP audit.
- Admin APIs y cron protegidos.

## Corregido hoy

No se hicieron fixes de codigo nuevos durante esta jornada diaria. Se crearon reportes y se verifico la V885 generada previamente.

## No probado

- Browser QA real.
- Capturas PC/movil reales.
- Telegram real.
- Pagos reales.
- Admin autenticado.
- Produccion V885, porque Render sigue en V855.

## Bloqueadores

P0: Render no esta desplegando V885. Produccion sigue en V855.

## Riesgos

- El usuario no vera la sidebar V885 hasta deploy correcto.
- `last_error` historico de header invalido sigue en runtime Render V855.
- Logos cache 0 en Render.
- OpenAI no configurado en Render.

## Prioridades

- P0: alinear GitHub/Render para que produccion sirva V885.
- P1: hacer browser QA PC/movil una vez Render muestre V885.
- P1: revisar logos cache 0 y fallback visual en produccion.
- P2: prueba Telegram controlada si el usuario la autoriza.

## Siguiente version recomendada

No crear nueva version hasta que Render sirva V885. Si tras deploy aparecen defectos visuales reales, crear:

`V886_REAL_RENDER_V885_BROWSER_QA_CLIENT_SIDEBAR_CERTIFICATION_FINAL`

## Prompt exacto para la siguiente ejecucion de Codex

Estoy trabajando en NeMeSiS SHARK PRO. Base local actual: `V885_CLIENT_SIDEBAR_RESTORE_BEST_POSITION_NAV_FINAL`. Produccion Render seguia en `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL`. Antes de crear features nuevas, verifica que GitHub/Render despliegan V885: consulta `/api/runtime-version`, confirma repo/rama/root/start command, documenta mismatch si existe, y si Render ya muestra V885 ejecuta Browser QA real PC/movil sobre `/app`, `/partidos`, `/live`, `/picks`, `/shark`, `/telegram`, `/profile` y admin protegido. No tocar secretos, no deploy automatico, no datos fake. Mantener Sentinel 10.0 y ZIP limpio.

## Prompt exacto para ChatGPT si se abre nueva conversacion

NeMeSiS SHARK PRO esta localmente en `V885_CLIENT_SIDEBAR_RESTORE_BEST_POSITION_NAV_FINAL`. Se restauro sidebar cliente PC, bottom nav movil sigue limpia, admin queda aislado. Sentinel local 10.0, ZIP limpio. Produccion Render aun sirve V855, por lo que el siguiente objetivo no es crear features: es alinear deploy GitHub/Render y certificar V885 en produccion con capturas reales.

## Estado produccion vs local

- Local: V885.
- Produccion: V855.
- Estado: mismatch critico.

## ZIP final

`release_output/NeMeSiS_SHARK_PRO_V885_CLIENT_SIDEBAR_RESTORE_BEST_POSITION_NAV_FINAL_RENDER_READY.zip`

## Accion humana requerida

Deploy manual correcto: subir contenido V885 a raiz GitHub, confirmar `VERSION.txt/app.py`, ejecutar Clear build cache & deploy en Render, reconsultar runtime.
