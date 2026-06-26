# V850 Live, Crests y API-SPORTS Current Audit

Base real usada: `V849_FULL_COMPANY_VISUAL_PRODUCT_EXPERIENCE_ADVANCEMENT`.

No se uso el ZIP viejo `NeMeSiS shark pro.zip` como base.

## Hallazgos

- `/live` y `/directo` ya agregaban fuentes cacheadas, live tracker API-Football y tablas locales.
- API-SPORTS/API-Football estaba protegido por `engines/api_sports_provider_engine.py` con cache-first, TTL, dry-run y guard anti-gasto.
- En local no hay key configurada, por tanto runtime muestra proveedor `not_configured`; esto es correcto para no exponer secretos.
- Las rutas de logos `/asset/team-logo` y `/asset/league-logo` ya usaban cache/fallback y no descargaban logos durante render.
- Habia textos visibles danados por mojibake en pantallas relacionadas con live/admin que debian corregirse.
- Faltaba una capa unificada V850 para score, minuto, estado y logo/fallback.

## Riesgos controlados

- No se anadio llamada externa por render.
- No se modifico `DB_PATH`.
- No se envio Telegram real.
- No se inventan marcador, minuto, resultado ni escudos oficiales.

## Correccion aplicada

- Nuevo `engines/live_match_experience_engine.py`.
- Nuevo `engines/crest_logo_experience_engine.py`.
- Filtros Jinja V850 para live cards y crest/logo payload.
- Mejoras visuales V850 en `/live`, `/calendar`, `/match/` y admin API-SPORTS.
