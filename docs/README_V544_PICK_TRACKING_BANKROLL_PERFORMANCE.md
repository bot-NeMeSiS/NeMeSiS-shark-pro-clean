# NeMeSiS SHARK PRO V544 — Pick Tracking + Bankroll Performance

Avance práctico sobre V543/V542 actual.

## Incluye

- Nueva ruta cliente `/seguimiento`.
- Tracking personal de picks publicados.
- Banca del usuario: inicial, actual, stake preferido y perfil de riesgo.
- APIs cliente:
  - `/api/client/pick-tracking`
  - `/api/client/bankroll`
  - `/api/client/track-pick`
- Nuevo panel admin `/admin/pick-performance`.
- API admin `/api/admin/pick-performance`.
- Tablas SQLite:
  - `user_pick_tracking`
  - `user_bankroll`
- Navegación cliente/admin actualizada.
- No inventa resultados: winrate/ROI se calcula solo con `result_status` real.
- ZIP limpio Render-ready.

## QA

- `app.py` compila OK.
- Migraciones seguras con SQLite.
- Mantiene `DB_PATH=/data/database.db`.
- Sin `.git`, sin `__pycache__`, sin DB local, sin logs basura.
