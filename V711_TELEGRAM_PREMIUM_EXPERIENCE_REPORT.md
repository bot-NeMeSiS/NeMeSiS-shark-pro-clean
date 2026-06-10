# V711 TELEGRAM PREMIUM EXPERIENCE

Objetivo: mejorar la experiencia de cliente en Telegram sin tocar el sistema Cron que ya funciona.

## Cambios aplicados

- Mensajes Telegram rediseñados con formato premium HTML.
- Partidos mucho más claros: competición, hora, estado, marcador si existe, local, visitante y enlace a la app.
- Picks automáticos más profesionales: pick recomendado, mercado, cuota, stake, SHARK Score, riesgo, value, motivo y precaución.
- Soporte de escudos/logos en Telegram cuando existan en datos:
  - `home_logo`
  - `away_logo`
  - `home_identity.crest_url`
  - `away_identity.crest_url`
  - caché de equipos desde `teams.logo_url`
  - fallback interno `/team-crest.svg` cuando hay URL pública disponible.
- Los escudos se muestran como enlaces visuales `🛡️` sobre el equipo correspondiente para que Telegram los pueda abrir/preview cuando exista URL HTTPS.
- Botones inline añadidos en mensajes de cola cuando hay URL de app:
  - Abrir calendario.
  - Abrir picks SHARK.
  - Ver análisis SHARK.
  - Abrir live SHARK.
- Preview de enlaces activable por payload para auto picks/live con logos.
- Enriquecimiento automático de picks desde la tabla `matches` para recuperar logos, hora, país y enlace `/match/<id>`.
- `APP_VERSION` actualizado a `V711_TELEGRAM_PREMIUM_EXPERIENCE`.

## Importante

Telegram no permite insertar dos imágenes inline dentro de un mismo mensaje de texto como si fuera HTML web normal. Por eso la mejora usa enlaces visuales de escudo y preview cuando hay URL HTTPS. En la app web los escudos siguen mostrándose como imagen normal.

Para que Telegram pueda abrir escudos fallback internos y botones, en Render conviene tener una de estas variables con la URL pública:

```env
PUBLIC_BASE_URL=https://bot-apuestas-crgf.onrender.com
```

o, si se prefiere:

```env
APP_PUBLIC_URL=https://bot-apuestas-crgf.onrender.com
```

Si no se pone, cuando el Cron llama al endpoint normalmente se puede usar `request.url_root`, pero la variable deja el comportamiento más estable.

## Validación local

- `python -m compileall -q .` OK
- `pytest -q` OK: 12 tests passed
- `python tools/smoke_check.py` OK, con los 2 avisos legacy ya conocidos de V710.
