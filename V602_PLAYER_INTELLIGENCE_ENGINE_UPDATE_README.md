# V602 — Player Intelligence Engine (actualización limpia)

## Qué contiene

Actualización pequeña para aplicar encima de la carpeta actual de NeMeSiS SHARK PRO V601.

Archivos incluidos:

- `app.py`
- `VERSION.txt`
- `engines/player_intelligence_engine.py`
- `templates/admin_data_center.html`
- `V602_PLAYER_INTELLIGENCE_ENGINE_REPORT.md`

## Qué añade

- Motor de inteligencia de jugadores.
- Perfiles de jugadores detectados desde alineaciones API-Football.
- Historial de bajas, dudas, lesiones y sanciones.
- Señales de impacto por equipo/partido.
- Integración con el scheduler `warehouse`.
- Integración en Admin Data Center.
- Endpoints:
  - `/api/player-intelligence/summary`
  - `/api/player-intelligence/rebuild`
  - `/api/player-intelligence/fixture`
  - `/api/v602/player-intelligence-check`

## Cómo aplicarlo

1. Descomprime este ZIP.
2. Copia los archivos encima de tu carpeta principal:
   `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`
3. Acepta reemplazar archivos.
4. Sube a GitHub.
5. Render redeploy.

## Variables

No necesita variables nuevas. Aprovecha datos ya guardados por V601/API-Football.

## Comprobación

Después del deploy, entra en:

- `/admin/data-center`
- `/api/v602/player-intelligence-check?public=1`

