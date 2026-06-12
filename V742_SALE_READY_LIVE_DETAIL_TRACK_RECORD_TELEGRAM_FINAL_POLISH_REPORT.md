# V742 Sale Ready Live Detail Track Record Telegram Final Polish

## Objetivo

V742 avanza la app hacia una versión comercial más vendible sin rehacer módulos ni inventar datos. El foco fue Live, Match Detail, Track Record real, Telegram Command Center, QA visual y control final admin.

## Cambios aplicados

### Live / Directo

- Añadidos alias seguros:
  - `/directo`
  - `/en-directo`
- Añadido motor `engines/live_experience_engine.py`.
- `/live` ahora usa filtros:
  - En directo
  - Hoy
  - Próximos
  - Finalizados
  - Con pick
  - Favoritos
  - España
  - Andalucía
  - Grandes ligas
- Añadido buscador por equipo, liga o país.
- Ordenación por directo, pick, favorito, competición importante y hora Madrid.
- Tarjetas con escudos/fallback, estado claro, marcador si existe y minuto solo si existe.

### Match Detail

- Añadidas acciones:
  - Volver al calendario.
  - Ver en directo si aplica.
  - Ver picks relacionados si existen.
- Añadidas secciones de Riesgos y Contexto.
- Si no hay datos suficientes, se muestra mensaje prudente.
- No se inventan estadísticas.

### Track Record / ROI

- `v742_track_record_context()` amplía el resumen real:
  - picks evaluables;
  - ganados;
  - perdidos;
  - nulos;
  - pendientes;
  - stake total;
  - beneficio;
  - ROI;
  - winrate;
  - por mes;
  - por liga;
  - por mercado;
  - por plan;
  - picks pendientes.
- `/track-record` se compactó para venta honesta.
- Si no hay resultados reales, muestra `Pendiente de resultados reales`.

### Telegram

- No se envió ningún mensaje automático durante validación.
- Se mantiene Telegram Command Center V727.
- El panel sale-ready consume el diagnóstico V727 y muestra estado Telegram resumido.
- En local el diagnóstico marca `MISSING_BOT_TOKEN`, esperado por ausencia de secrets Render.

### Sale Ready

- Añadido `/admin/sale-ready`.
- Añadido alias `/admin/commercial-ready`.
- Añadido `/api/admin/sale-ready`.
- Añadido `/admin/live-experience`.
- Añadido alias `/admin/live-qa`.
- Añadido `/api/admin/live-experience`.
- Consolida:
  - Live;
  - Calendario;
  - Picks;
  - Track Record;
  - Telegram;
  - Visual/móvil;
  - Render;
  - DB/Data Memory;
  - warnings pendientes.

### Visual / móvil

- Capa CSS V742 para:
  - buscador Live;
  - tarjetas Live;
  - nombres largos;
  - Match Detail;
  - Track Record;
  - panel sale-ready;
  - prevención de overflow en móvil.

### Estabilidad Render / DB limpia

- La home queda protegida ante bases nuevas o migraciones donde todavía no existan `favorites` o `persistent_cache`.
- `/` ya no depende de alertas cliente si la caché persistente no está inicializada.
- La portada mantiene fallback limpio y carga 200 en smoke test con SQLite temporal.
- Se eliminaron copias HTML antiguas en la raíz del proyecto; las plantillas oficiales quedan solo en `templates/`.

## Rutas nuevas

- `/directo`
- `/en-directo`
- `/admin/sale-ready`
- `/admin/commercial-ready`
- `/api/admin/sale-ready`
- `/admin/live-experience`
- `/admin/live-qa`
- `/api/admin/live-experience`

## Qué no se tocó

- Secrets reales.
- `DB_PATH=/data/database.db`.
- Cron.
- Telegram automático.
- Pagos reales.
- Membresías reales.
- Madrid Time.
- Calendario V741.
- Picks V740.

## Validación pendiente de producción real

- Envío Telegram real con bot/canal de Render.
- Datos reales de `/data/database.db`.
- Cron real de Render.
- Cobertura real de partidos/cuotas.
- QA visual en móvil físico.

## Validación ejecutada

- `python -m compileall -q app.py engines services blueprints tools tests database_manager.py`: OK.
- `tools/check_v728_client_experience.py`: OK.
- `tools/check_v729_security.py`: OK.
- `tools/check_v730_route_health.py`: OK con avisos legacy no bloqueantes.
- `tools/check_v731_client_experience.py`: OK.
- `tools/check_v733_client_success.py`: OK.
- `tools/check_v735_go_live.py`: OK.
- `tools/check_v736_visual_experience.py`: OK.
- `tools/check_v737_app_feel.py`: OK.
- `tools/check_v738_final_release.py`: OK.
- `tools/check_v739_home_data.py`: OK.
- `tools/check_v740_client_visual_pick_analysis.py`: OK.
- `tools/check_v741_calendar_experience.py`: OK.
- `tools/check_telegram_reliability.py`: OK en local con estado esperado `MISSING_BOT_TOKEN`.
- `tools/check_v742_live_experience.py`: OK.
- `tools/check_v742_track_record.py`: OK.
- `tools/check_v742_sale_ready.py`: OK.
- Smoke Flask con SQLite temporal: `/`, `/admin-login`, `/sports-hub`, `/live`, `/directo`, `/calendar`, `/picks`, `/combis`, `/favorites`, `/track-record`, `/telegram`, `/shark`, `/guia`, `/ayuda`, APIs y paneles admin clave sin 500.
