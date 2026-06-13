# V758_ADAPTIVE_DESKTOP_MOBILE_TOP_APP_EXPERIENCE

## Objetivo
Mejora grande de experiencia general para PC, tablet y móvil sin tocar Telegram/Cron/DB_PATH.

## Implementado
- Motor `engines/adaptive_experience_engine.py` para detectar modo PC/tablet/móvil de forma defensiva.
- Rutas `/experiencia`, `/modo-app`, `/adaptive`, `/adaptativo`.
- API `/api/client/device-experience` protegida para clientes logueados.
- Bloques V758 insertados en Home, App Center, Picks, Calendar, Live, Match Detail y Track Record.
- Script en `base.html` que añade clases `ns-device-mobile`, `ns-device-tablet` o `ns-device-desktop` según ancho real del navegador.
- CSS V758 con navegación móvil más táctil, layout PC más ancho, tarjetas adaptativas, safe-area mobile y accesos rápidos.

## Conservado
- Telegram automático V754.
- Render Cron runner.
- `AUTOMATION_SECRET`.
- `DB_PATH`.
- Usuarios, membresías y Madrid Time.

## Validación esperada
Ver `/experiencia`, `/app`, `/calendar`, `/picks`, `/live`, `/track-record` en PC y móvil.
