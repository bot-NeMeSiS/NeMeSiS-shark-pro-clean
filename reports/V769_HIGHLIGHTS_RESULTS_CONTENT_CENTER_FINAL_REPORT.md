# V769 Highlights / Results Content Center Final

## Objetivo
Convertir los highlights/resúmenes en una capa definitiva de producto: útil para cliente, conectada con resultados, partido, calendario, Track Record y admin, sin descargar ni rehostear vídeos.

## Cambios principales
- Versión actualizada a `V769_HIGHLIGHTS_RESULTS_CONTENT_CENTER_FINAL`.
- Refuerzo de `engines/sportsdb_highlights_engine.py`:
  - columna `embed_url` para YouTube-nocookie cuando el enlace permite iframe.
  - columna `rights_note` para política de uso.
  - columna `client_status` para diferenciar `EMBED_READY`, `LINK_READY` y `NO_VIDEO`.
  - conversión segura de enlaces YouTube/youtu.be/shorts/embed a `youtube-nocookie`.
- Nuevo centro de contenido V769 en `app.py`:
  - `v769_highlights_content_center()`.
  - `v769_highlight_card_from_row()`.
  - `v769_pending_highlight_matches()`.
  - `v769_get_highlight_by_id()`.
- Nuevas rutas cliente:
  - `/resumen/<highlight_id>`.
  - `/highlight/<highlight_id>`.
  - `/resumenes/<highlight_id>`.
- Nueva API cliente:
  - `/api/client/highlights/content-center`.
- Nuevo panel admin:
  - `/admin/highlights-center`.
  - `/admin/resumenes`.
  - `/api/admin/highlights/status`.
- Nuevo runner Render Cron:
  - `tools/render_cron_highlights_sync.py`.
- Nuevo template cliente:
  - `templates/highlight_detail.html`.
- Nuevo template admin:
  - `templates/admin_highlights_center.html`.
- `templates/highlights.html` reescrito como centro real de resultados/resúmenes.
- `templates/match_detail.html` ahora muestra resumen embebido si está disponible.
- `templates/home.html` muestra últimos resúmenes sin saturar.
- `templates/track_record.html` añade evidencia visual de resultados.
- Navegación admin incluye Resúmenes.
- CSS V769 añadido para cards, iframe, grid responsive y paneles.

## Automatización recomendada en Render
Crear un Cron Job separado para highlights:

```bash
python tools/render_cron_highlights_sync.py
```

Variables necesarias en el Cron:

```bash
PUBLIC_BASE_URL=https://bot-apuestas-crgf.onrender.com
AUTOMATION_SECRET=***hidden***
HIGHLIGHTS_DAYS_BACK=7
HIGHLIGHTS_LIMIT=300
```

El endpoint protegido usado por el runner es:

```text
/api/automation/highlights/sync?secret=AUTOMATION_SECRET&days_back=7&limit=300
```

## Política legal / contenido
La app no descarga, copia ni rehostea vídeos. Solo guarda metadatos y enlaces externos aportados por la API. Cuando sea YouTube, puede usar iframe `youtube-nocookie` para verlo dentro de la app, siempre como contenido externo.

## Preservado
- Telegram automático.
- `/api/automation/telegram/tick`.
- `tools/render_cron_telegram_tick.py`.
- `AUTOMATION_SECRET`.
- `DB_PATH`.
- Usuarios/sesiones/membresías.
- Pagos reales.
- Madrid Time.
- V755 Telegram normalization.
- V768 pick grading/certificación.

## Limitaciones honestas
No se hizo llamada real a TheSportsDB desde sandbox porque no hay secrets reales. La disponibilidad de vídeos depende de TheSportsDB/YouTube y de si la fuente externa publica highlights para ese partido.
