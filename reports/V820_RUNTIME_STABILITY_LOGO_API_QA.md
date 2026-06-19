# V820 Runtime Stability Logo API QA

## Principio

Los logos no pueden tumbar la web.

## Medidas

- `crest_engine` no descarga imagenes en render.
- Solo sanitiza y usa URLs ya guardadas.
- Si una URL falla en navegador, el fallback queda visible.
- Endpoints `/asset/team-logo` y `/asset/league-logo` redirigen a URL real solo si existe cache segura.
- Si no hay cache, redirigen al fallback local.

## Render

No se toca `render.yaml`, `Procfile`, DB_PATH, Cron ni scheduler.
