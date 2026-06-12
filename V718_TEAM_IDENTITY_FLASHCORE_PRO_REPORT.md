# V718_TEAM_IDENTITY_FLASHCORE_PRO

## Objetivo
Subir la experiencia visual de partidos al nivel de app deportiva profesional tipo Flashscore/Sofascore, reforzando escudos, banderas, identidad de equipos y fallbacks seguros sin romper Render, Telegram, Cron, DB_PATH ni la calibración de Telegram solo fútbol.

## Cambios principales

### 1. Motor central de identidad de equipos
Añadido `engines/team_identity_engine.py` con helpers seguros:

- `safe_logo_url()` para evitar URLs rotas, valores `None/null/undefined` o enlaces peligrosos.
- `identity_payload()` para construir identidad visual completa.
- `merge_identity()` para fusionar datos de base/cache/API sin romper.
- banderas/emoji para selecciones reconocidas.
- fallback propio con `/team-crest.svg` cuando no hay logo real.
- SVG inline de emoji/bandera cuando aplica.

### 2. Identidad aplicada a partidos y picks
Se refuerza la identidad en:

- `resolve_team()`
- `annotate_match()`
- `get_matches()`
- `get_upcoming_matches()`
- `normalize_pick_row()`

Cada partido/pick puede llevar ahora:

- `home_identity`
- `away_identity`
- `crest_url`
- `crest_mode`
- `ui_class`
- `flag_emoji`
- `initials`
- `home_badge_text`
- `away_badge_text`

### 3. Pantallas visuales mejoradas
Se actualizan templates para usar clases y fallback PRO:

- `sports_hub.html`
- `live.html`
- `calendar.html`
- `picks.html`
- `combis.html`
- `favorites.html`
- `match_detail.html`
- `match_hub.html`
- `team_detail.html`
- `crests.html`

Los picks ahora muestran bloque visual de equipos con escudos/fallbacks en las tarjetas premium.

### 4. CSS de escudos PRO
Añadidos estilos en `static/app.css`:

- `.crest-logo`
- `.crest-flag`
- `.crest-fallback`
- `.team-emoji`
- `.pick-teams-pro`
- `.pick-team-pro`

Se evita el aspecto de letras gigantes feas y se mejora el look compacto.

### 5. Diagnóstico admin de identidad
Añadida vista protegida:

- `/admin/team-identity`

Y API admin protegida:

- `/api/admin/team-identity`

Muestra:

- equipos con logo
- equipos usando fallback
- partidos con ambos logos
- partidos con algún logo faltante
- porcentaje de cobertura
- muestras con fallback aplicado

## Archivos tocados

- `app.py`
- `VERSION.txt`
- `engines/team_identity_engine.py`
- `static/app.css`
- `templates/admin_team_identity.html`
- `templates/sports_hub.html`
- `templates/live.html`
- `templates/calendar.html`
- `templates/picks.html`
- `templates/combis.html`
- `templates/favorites.html`
- `templates/match_detail.html`
- `templates/match_hub.html`
- `templates/team_detail.html`
- `templates/crests.html`

## Validación ejecutada

- `python -m py_compile app.py`: OK
- `python -m py_compile engines/team_identity_engine.py`: OK
- `python -m compileall -q app.py engines templates`: OK
- Parseo Jinja de templates: OK
- Prueba directa del motor de identidad: OK

No se ejecutó smoke Flask completo porque este entorno no tiene Flask instalado, pero no se ha tocado configuración de Render/Cron/Telegram/DB.

## Qué se mantiene intacto

- Telegram automático.
- Cron Jobs.
- `AUTOMATION_SECRET`.
- `DB_PATH=/data/database.db`.
- Login/registro.
- Membresías.
- Picks.
- Combis hasta 15.
- Filtro Telegram solo fútbol.
- Calibración PRO de Telegram.

## Cómo probar en Render

1. Subir el ZIP.
2. Abrir `/api/runtime-version`.
3. Debe mostrar `V718_TEAM_IDENTITY_FLASHCORE_PRO`.
4. Revisar:
   - `/sports-hub`
   - `/live`
   - `/calendar`
   - `/picks`
   - `/combis`
   - `/match/<id>`
   - `/admin/team-identity`
5. Confirmar que no hay imágenes rotas y que los equipos sin escudo usan fallback compacto o bandera.

## Pendiente dependiente de datos reales

La cobertura real de escudos depende de los logos disponibles en la base `/data/database.db`, TheSportsDB y datos ya cacheados. Si un equipo no tiene logo real, la app usará fallback profesional en vez de romper la imagen.
