# V540 — Live Data Intelligence + Real Match Depth

Avance centrado en profundidad real del partido y contexto deportivo sin inventar datos.

## Incluye

- Enriquecimiento de `/match/<id>` con forma reciente local/visitante.
- Enfrentamientos directos guardados desde SQLite.
- Lectura contextual SHARK por partido.
- API nueva `/api/matches/<match_id>/depth`.
- Ruta de health `/v540-health`.
- Bloques visuales V540 en match detail y team detail.
- Mejoras CSS mobile para forma, mini estadísticas y listas compactas.
- No usa scraping ilegal.
- No inventa resultados ni picks como reales.
- Mantiene DB_PATH=/data/database.db.

## QA

- `python -m py_compile app.py` OK.
- ZIP limpio sin `.git`, `__pycache__`, DB local, logs ni ZIPs antiguos.
