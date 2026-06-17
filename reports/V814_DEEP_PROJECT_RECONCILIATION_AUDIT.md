# V814 Deep Project Reconciliation Audit

## Versión base detectada

- `VERSION.txt`: `V813_CODEX_FULL_ECOSYSTEM_RESTRUCTURE_REFERENCE_SELL_READY`.
- `app.py APP_VERSION`: `V813_CODEX_FULL_ECOSYSTEM_RESTRUCTURE_REFERENCE_SELL_READY`.
- V813 estaba aplicada de verdad: shell `data-v813-shell`, checks V813, informes V813, filtro Telegram profesional y ZIP V813 existían.

## Versión reconciliada

V814 deja `VERSION.txt` y `APP_VERSION` en:

`V814_CODEX_DEEP_PROJECT_RECONCILIATION_CLIENT_ADMIN_REFERENCE_FINAL`

## Mezclas y restos encontrados

- La app activa conserva capas visuales históricas V797, V805, V810, V811, V812 y V813 dentro de `static/app.css`.
- Esa mezcla no rompe por sí sola porque las reglas están acotadas con `data-vXXX-shell`, pero dificulta mantenimiento y puede generar pelea visual si no hay una capa final clara.
- Hay módulos antiguos duplicados en raíz (`api_exploitation_engine.py`, `live_engine.py`, `football_data_warehouse_engine.py`, `membership_engine.py`, etc.) y versiones actuales dentro de `engines/` o `services/`.
- Hay informes históricos V5xx-V7xx en raíz. Son trazabilidad, no runtime.
- Hay `.venv`, `.pytest_cache`, `__pycache__`, `v636work`, `release_output` con ZIPs antiguos y una DB local de smoke.
- No se detectó que esos restos entren en runtime principal de Render si se usa el ZIP limpio.

## Archivos oficiales activos

- `app.py`
- `database_manager.py`
- `engines/`
- `services/`
- `templates/`
- `static/`
- `tools/`
- `tests/`
- `blueprints/`
- `requirements.txt`
- `Procfile`
- `render.yaml`
- `.env.example`
- `.env.render.clean`
- `README_MASTER.md`
- `VERSION.txt`
- `CHATGPT_CONTINUATION_REPORT.md`

## Basura o legado que debe quedar fuera del release

- `.git/`
- `.venv/`
- `.pytest_cache/`
- `__pycache__/`
- `v636work/`
- `release_output/` antiguo
- bases locales `.db`
- logs
- ZIPs internos
- vídeos/capturas
- backups locales

## Decisión V814

No se borraron motores, plantillas ni informes históricos activos de forma destructiva. La reconciliación se hace con:

- versión V814 única;
- capa visual V814 final;
- checks V814;
- release builder que excluye basura;
- auditoría ZIP con `forbidden_count = 0`.
