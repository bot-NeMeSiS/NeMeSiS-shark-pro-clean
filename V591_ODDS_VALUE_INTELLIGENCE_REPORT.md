# V591 — Odds & Value Intelligence

## Objetivo
Mejorar la lectura de cuotas y value sin crear pantallas nuevas ni forzar llamadas extra a APIs.

## Añadido
- Motor `engines/odds_value_engine.py`.
- Tablas SQLite seguras:
  - `odds_value_signals`
  - `odds_value_summary`
- Cálculo de probabilidad implícita desde cuota.
- Lectura conservadora de probabilidad SHARK desde confianza.
- Señales de value:
  - Value fuerte
  - Value moderado
  - En observación
  - Precio justo
  - Sin value
- Integración en ficha de partido V590.
- Integración en Admin Data Center.
- Endpoints:
  - `/api/odds-value/summary`
  - `/api/odds-value/rebuild`
  - `/api/v591/odds-value-check`

## Seguridad
- No inventa cuotas.
- No fuerza llamadas a The Odds API.
- Usa `odds_snapshots`, picks y recomendaciones ya guardadas.
- No rompe Telegram, Auto Picks, SHARK Learning, membresías, login ni Render.

## Archivos modificados
- `app.py`
- `engines/odds_value_engine.py`
- `templates/match_detail.html`
- `templates/admin_data_center.html`
- `static/app.css`
- `VERSION.txt`

## Validación
- Compileall ejecutado sobre `app.py` y `engines/`.
- ZIP preparado limpio para GitHub/Render.
