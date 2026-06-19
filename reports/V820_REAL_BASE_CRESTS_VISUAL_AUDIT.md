# V820 Real Base Crests Visual Audit

## Base real usada

- Carpeta oficial: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`.
- Base obligatoria detectada: `V819_REFERENCE_UI_DEDUP_LAYER_PURGE_CLIENT_ADMIN_FINAL`.
- Version final aplicada: `V820_REAL_CRESTS_REFERENCE_VISUAL_PIXEL_POLISH_FINAL`.

No se uso el ZIP grande historico porque el propio encargo indica que puede contener V818/V815, cache CSS antigua, `.git`, `.venv`, caches y estructura anidada. La fuente real es la carpeta oficial V819.

## Estado de escudos antes de V820

La app ya tenia:

- columnas `matches.home_logo` y `matches.away_logo`;
- columna `teams.logo_url`;
- ruta fallback `/team-crest.svg?name=...`;
- macro `partials/team_identity.html`;
- integracion previa con TheSportsDB/API-Football cuando el dato ya estaba guardado.

El problema era que `engines/crest_engine.py` era minimo y no centralizaba cache, resolucion, seguridad y trazabilidad. Por eso muchos partidos terminaban visualmente en fallback generico.

## Cambio V820

Se refuerza `engines/crest_engine.py` como motor central:

- valida URLs;
- convierte HTTP a HTTPS;
- rechaza URLs inseguras;
- crea cache SQLite `team_logo_cache` y `league_logo_cache`;
- resuelve payload de equipo/liga;
- mantiene fallback SVG local como ultimo recurso;
- no descarga imagenes ni bloquea render.

## Datos reales de logo disponibles

La aplicacion usa logos reales si existen en:

- `matches.home_logo`;
- `matches.away_logo`;
- `teams.logo_url`;
- caches V820;
- payloads ya enriquecidos por proveedores.

Si no existe logo real, V820 muestra fallback elegante y marcado internamente como fallback.
