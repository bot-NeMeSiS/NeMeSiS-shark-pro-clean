# V716 Professional Client Experience Maximum Upgrade

## Objetivo

Elevar NeMeSiS SHARK PRO al máximo nivel profesional posible antes de venta, sin rehacer la aplicación y sin romper Render, Telegram automático, Cron Jobs, seguridad V715, login, admin, membresías ni SQLite persistente.

## Problemas encontrados

- `/dashboard` estaba redirigiendo a Sports Hub y no funcionaba como panel cliente propio.
- La home cliente mostraba versión interna como señal principal.
- Picks publicados sin cuota real o sin selección podían aparecer junto a picks premium.
- Algunas métricas mostraban `0%`, `FT`, `Auto` o estados poco comerciales sin suficiente contexto.
- Combis mostraba un carrusel largo de botones 2-15 que generaba sensación de herramienta técnica.
- SHARK podía usar picks incompletos para respuestas si tenían selección pero no cuota real.
- La página Telegram era funcional, pero podía explicar mejor la vinculación.
- La página de membresías tenía textos correctos, pero poco comerciales y sin aviso responsable explícito.

## Mejoras aplicadas

### Cliente y Home

- Se eliminó la versión técnica visible en la home.
- Se sustituyó por señales comerciales: radar deportivo activo, partidos, directos, picks y Telegram.
- Se limpió la navegación cliente: Inicio, Partidos, Directo, Picks, Combis, SHARK y Más.
- La barra móvil queda más compacta y reduce saturación visual.

### Dashboard cliente

- `/dashboard` vuelve a ser una pantalla real.
- Nueva estructura:
  - Hoy en NeMeSiS.
  - Acciones rápidas.
  - Mejores señales SHARK.
  - Partidos destacados.
  - Tu actividad.
- No muestra winrate, ROI o cuota media cuando no hay histórico suficiente.

### Picks premium

- Se añadió validación comercial central:
  - partido no antiguo,
  - cuota real,
  - selección clara,
  - sin textos tipo pendiente/undefined/null.
- Los picks válidos aparecen como “Picks listos para entrar”.
- Los picks incompletos aparecen como “En estudio por SHARK”.
- Se tradujeron selecciones:
  - `Local` -> `Gana [equipo local]`
  - `Visitante` -> `Gana [equipo visitante]`
  - `Over 2.5` -> `Más de 2.5 goles`
  - `Under 2.5` -> `Menos de 2.5 goles`
  - `BTTS Yes` -> `Ambos equipos marcan: Sí`

### Combis hasta 15

- Se mantiene máximo 15.
- Se sustituyó el scroll de botones 2-15 por:
  - Combi segura,
  - Combi media,
  - Combi larga,
  - selector compacto de 2 a 15.
- Las combis usan picks publicados con cuota real cuando existen.
- Si no hay suficientes selecciones válidas, se muestra estado claro y no se fabrican apuestas.

### SHARK AI

- El widget tiene botones rápidos más completos:
  - Pick de hoy,
  - Mejores picks,
  - Combi segura,
  - Combi 15,
  - Directo,
  - Favoritos,
  - Oportunidades,
  - Riesgo,
  - Qué partido ver,
  - Explicar apuesta,
  - Resumen del día.
- SHARK ya no muestra rutas internas tipo `Abrir: /picks`.
- SHARK usa solo picks comercialmente válidos para respuestas premium.
- En combi segura limita a 2-4 selecciones aunque el usuario pida más.
- Si no hay datos suficientes, responde con aviso claro sin inventar cuotas ni partidos.

### Telegram

- Se mantiene intacto el flujo automático, cola, Cron y endpoints protegidos.
- Los mensajes se benefician de la misma normalización de selecciones.
- La pantalla cliente de Telegram incluye:
  - estado conectado/no conectado,
  - pasos de vinculación,
  - botón copiar código,
  - qué recibirá según membresía.

### Membresías

- Se reescribieron textos FREE / PRO / ELITE con enfoque comercial.
- Se añadió aviso responsable:
  “NeMeSiS SHARK PRO ofrece análisis deportivo y señales de valor. No garantiza resultados. Apuesta siempre con responsabilidad.”

### Match Detail

- Se evitaron métricas crudas `0` en SHARK Score, presión y riesgo cuando no hay datos suficientes.
- Se muestran estados como “En cálculo”, “Contextual” o “Controlado”.

## Archivos modificados

- `app.py`
- `VERSION.txt`
- `templates/base.html`
- `templates/home.html`
- `templates/client_overview.html`
- `templates/picks.html`
- `templates/combis.html`
- `templates/telegram.html`
- `templates/shark.html`
- `templates/match_detail.html`
- `templates/membership.html`
- `static/app.css`
- `V716_PROFESSIONAL_CLIENT_EXPERIENCE_MAXIMUM_UPGRADE_REPORT.md`

## Validación

- `python -m py_compile app.py`: OK
- `python -m compileall -q .`: OK
- `python tools/smoke_check.py`: OK
- `pytest -q`: no ejecutable en este entorno porque `pytest` no está instalado.

### Smoke manual con Flask test client

- `/`: 200
- `/version`: 200
- `/api/runtime-version`: 200
- `/login`: 200
- `/cliente-login`: 200
- `/admin-login`: 200
- `/registro`: 200
- `/sports-hub`: 200
- `/live`: 200
- `/calendar`: 200
- `/picks`: 200
- `/combis`: 200
- `/shark`: 200
- FREE `/dashboard`: 200
- FREE `/perfil`: 200
- FREE `/telegram`: 200
- FREE `/favorites`: 200
- FREE `/picks`: 200
- FREE `/combis`: 200
- FREE `/shark`: 200
- ELITE `/dashboard`: 200
- ELITE `/perfil`: 200
- ELITE `/telegram`: 200
- ELITE `/favorites`: 200
- ELITE `/picks`: 200
- ELITE `/combis`: 200
- ELITE `/shark`: 200
- `/api/automation/telegram/tick` sin secret: 403
- `/api/automation/telegram/tick?secret=...`: 200
- `/api/automation/daily/run` sin secret: 403
- `/api/automation/daily/run?secret=...`: 200
- `/api/runtime-version` devuelve `V716_PROFESSIONAL_CLIENT_EXPERIENCE_MAXIMUM_UPGRADE`

## Cómo probar en Render

1. Desplegar el ZIP Render Ready.
2. Confirmar `/api/runtime-version`.
3. Abrir `/`, `/dashboard`, `/sports-hub`, `/picks`, `/combis`, `/telegram`, `/shark`.
4. Confirmar que los Cron Jobs siguen apuntando a:
   - `/api/automation/telegram/tick?secret=AUTOMATION_SECRET`
   - `/api/automation/daily/run?secret=AUTOMATION_SECRET`
5. Confirmar que sin secret devuelven 403 y con secret 200.

## Pendiente real

- Validar Telegram real en producción con red externa y bot activo.
- Validar escudos reales según cobertura de APIs externas.
- Validar volumen real de picks/cuotas cuando Render tenga datos frescos.
