# V884 Visual Layout Functionality QA

## Objetivo

Conectar visual y funcion: una pantalla premium debe verse bien y tambien guiar al usuario.

## Reglas activas

- No admin nav en cliente.
- No bottom nav cliente en admin.
- No floating SHARK cliente en admin.
- No enlaces vacios.
- No CTAs sin destino.
- No CTAs repetidos sin jerarquia.
- No estados vacios sin accion segura.

## Cambios

- `templates/base.html` marca V884 funcional.
- `engines/visual_company_worker_engine.py` ahora inspecciona links y flujo.
- `engines/continuous_shark_sentinel_engine.py` expone reglas V884.

## No probado

- No se hizo browser QA con capturas reales.
- No se declara pixel-perfect.
