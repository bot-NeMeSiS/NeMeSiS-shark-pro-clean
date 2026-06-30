# V860 Project Cleanup And Legacy Audit

## Estado general

- La carpeta oficial sigue mezclando source activo con material histórico, release artifacts y caches locales.
- El problema principal no es el ZIP final actual, sino la densidad de capas antiguas y residuos alrededor del source.

## Crítico que debe quedarse

- `app.py`
- `VERSION.txt`
- `templates/`
- `static/`
- `engines/`
- `tools/`
- `services/`
- `blueprints/`
- `reports/` actuales
- `.env.example`
- `.env.render.clean`
- `requirements*.txt`
- `Procfile`
- `render.yaml`

## Basura / ruido detectado

- `release_output/`: 59 ZIPs locales históricos.
- `data/`: 54 bases locales y de checks. No se tocan automáticamente por la regla de preservar `DB_PATH` y no borrar DB real.
- `__pycache__/`: 109 directorios detectados en todo el árbol, la mayoría dentro de `.venv`; también hay caches fuera del entorno virtual.
- `.pytest_cache/`: presente.
- `.venv/`: presente y grande; debe excluirse siempre del release.
- `v636work/`: árbol legacy sospechoso que no debe entrar en release.

## Legacy visual detectado

- `static/app.css` mantiene bloques desde V5xx, V7xx, V8xx y V85x acumulados.
- `templates/base.html` mezcla varias capas de navegación y decoraciones activas según rol.
- Admin estaba sobrecargado con top nav + rail + dock + command strip.
- Cliente mezcla top nav, top quick actions, rail lateral, bottom nav y floating SHARK.

## Riesgo

- Seguir añadiendo polish sobre esta base sin purga controlada seguiría degradando coherencia y mantenibilidad.
