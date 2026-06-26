# V847 API-SPORTS Current Usage Audit

Base real usada: `V845_SHARK_AI_INTELLIGENCE_PRODUCT_ASSISTANT_FINAL`.

Fuente de verdad: carpeta oficial `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`. No se usó el ZIP viejo `NeMeSiS shark pro.zip`.

## Configuración

- API-SPORTS/API-Football en código: sí.
- Variables aceptadas: `API_FOOTBALL_KEY`, `API_FOOTBALL_API_KEY`, `API_SPORTS_KEY`, `APISPORTS_KEY`.
- Entorno local en esta auditoría: se detecta sin mostrar valor mediante runtime/checks. Si no hay variable, runtime responde `api_sports_configured=false`.
- The Odds API sigue separado para cuotas mediante `THE_ODDS_API_KEY` o `ODDS_API_KEY`.

## Uso encontrado

- `engines/api_football_live_tracker_engine.py`: proveedor API-Football live/detail/window con `x-apisports-key`.
- `engines/api_exploitation_engine.py`: explotación avanzada de fixtures, lineups, injuries, standings, h2h y estadísticas.
- `/live` y `/directo`: sincronizan live tracker si procede y mezclan con cache local.
- `/match/`: refresca detalle API-Football con cache corto por partido.
- V818 master tick: mantiene sync window/live protegido por secret.
- `templates/live.html` y `templates/match_detail.html`: muestran evidencia API-Football si existe.

## Huecos detectados

- No existía una fachada única para decir si API-SPORTS está realmente configurada y activa.
- Runtime no exponía `api_sports_configured`, `provider_active`, `last_sync`, `last_error` ni `usage_guard`.
- Admin/Data Center no tenía panel claro para explicar cache, proveedor y guard anti-gasto.
- SHARK no recibía un estado explícito del proveedor para explicar “Esperando proveedor” o “API-SPORTS no configurada”.

## Corrección V847

- Nuevo `engines/api_sports_provider_engine.py`.
- Nuevo `/admin/api-sports` y alias `/admin/api-sports-audit`.
- Nuevo `/api/admin/api-sports/status` y alias `/api/admin/api-sports-audit`.
- Runtime ampliado con proveedor activo, cache, last sync, last error y guard anti-gasto.
- Data Center y SHARK reciben resumen seguro del proveedor.

## Riesgo de créditos

V847 no añade llamadas externas automáticas por render. La fachada es cache-first, soporta dry-run y solo llama al proveedor con acción explícita.
