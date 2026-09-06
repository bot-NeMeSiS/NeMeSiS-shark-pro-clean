# Mapa Completo del Ecosistema NeMeSiS

## Superficies cliente

- Acceso: Landing, Login, Registro y recuperacion.
- Sports: Home, Partidos/Calendario, Directo, Match, Team, Competition y Player.
- Inteligencia: Picks, SHARK, Combis y Track Record.
- Cuenta: Membresias, Telegram, Perfil, Seguridad y Soporte.

## Superficies internas

- Admin Dashboard y usuarios/membresias.
- Founder Center, Product Review y Executive Board.
- Sports/Data, Operations, Observability y backups.
- Growth, Revenue, Payments y Data Marketplace.
- Automation, Quality Division, Sentinel, Product Memory y Prepared for Codex.

## Flujo deportivo canonico

`PROVIDER -> CACHE/DB -> SPORTS TRUTH -> DOMAIN CONTRACT -> SURFACE CONTRACT -> UI`

La observacion del proveedor conserva `last_synced_at`; persistir o leer una
entidad no cambia por si mismo su frescura.

- Sports Truth: `engines/v935_launch_trust_engine.py`.
- Realtime cache-only: `engines/v934_realtime_sports_engine.py`.
- Directo: `engines/live_match_experience_engine.py`.
- Match Center: `engines/match_context_engine.py`.
- Madrid Time: `engines/madrid_time_engine.py`.
- Entidades: `engines/sports_domain_model_engine.py` y contratos de `app.py`.
- Relevancia: funciones canonicas de relevancia en `app.py`.

## Datos y proveedores

- SQLite local/produccion segun `DB_PATH`; produccion declara `/data/database.db`.
- API-Football/API-Sports: fixtures, live y enriquecimiento segun plan/cuota.
- TheSportsDB: identidad/enriquecimiento/highlights segun cobertura y derechos.
- The Odds API: cuotas; no gobierna relevancia deportiva.
- Media Rights: fail-closed; no rehost, no stream y no derechos asumidos.

## Automatizacion

- Render web service con disco persistente.
- Cron existente `telegram-auto-tick` ejecuta `render_cron_master_tick.py`.
- Master Scheduler orquesta flujos autorizados.
- Continuous Evolution observa, analiza, recuerda y prepara; no cambia produccion solo.

## Calidad

- Pytest, Jinja, rutas, smoke, privacy/secret guards.
- Sports Truth, Digital User, Visual Inspector, Regression Manager y Production Sentinel.
- QA automatica no sustituye aprobacion visual subjetiva del Founder.

## Escala actual

- 4.089 archivos versionados.
- 778 decoradores de ruta (incluye aliases).
- 199 templates, 157 engines y 55 ficheros de test.
- `app.py` conserva deuda estructural con 27.849 lineas en el candidato local;
  no se aborda en esta fase.
