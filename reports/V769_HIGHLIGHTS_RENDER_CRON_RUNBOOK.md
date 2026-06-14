# V769 Highlights Render Cron Runbook

## Objetivo
Mantener resúmenes/highlights actualizados automáticamente sin intervención manual.

## Cron recomendado
Crear un nuevo Render Cron Job con:

```bash
python tools/render_cron_highlights_sync.py
```

## Variables requeridas

```bash
PUBLIC_BASE_URL=https://bot-apuestas-crgf.onrender.com
AUTOMATION_SECRET=<mismo valor que el Web Service>
THESPORTSDB_API_KEY=<en Web Service, no necesariamente en Cron>
```

Opcionales:

```bash
HIGHLIGHTS_DAYS_BACK=7
HIGHLIGHTS_LIMIT=300
```

## Frecuencia sugerida
- 09:30 Madrid: primera pasada de partidos recientes.
- 23:45 Madrid: segunda pasada en días con muchos partidos.

## Verificación
Después de ejecutar el Cron, abrir:

```text
/admin/highlights-center
/api/admin/highlights/status
/resumenes
/calendar?lane=results
```

## Estados esperados
- `EMBED_READY`: vídeo visible dentro de la app mediante iframe externo.
- `LINK_READY`: enlace externo disponible, pero no iframe.
- `NO_VIDEO`: TheSportsDB no aportó vídeo.
- `Resumen pendiente`: partido finalizado sin resumen todavía.

## Seguridad
No exponer `AUTOMATION_SECRET` en cliente. El endpoint de automatización debe devolver 403 sin secret válido.
