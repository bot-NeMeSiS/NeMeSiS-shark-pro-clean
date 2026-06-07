# V542 — Smart Discovery + Commercial Readiness

Avance aplicado sobre el ZIP real completo subido por el usuario.

Incluye:
- Nueva ruta cliente `/explorar`.
- Buscador premium de partidos, equipos, ligas y picks.
- API `/api/discovery/search`.
- Nuevo panel admin `/admin/commercial-readiness`.
- API `/api/admin/commercial-readiness`.
- Score interno de preparación comercial.
- Navegación cliente/admin actualizada.
- CSS responsive para buscador y checklist.

Mantenido:
- Login, usuarios, roles y membresías.
- Match Hub, Live, resultados, picks, combinadas y favoritos.
- SHARK IA y paneles admin existentes.
- DB_PATH=/data/database.db.

QA local:
- app.py compila OK.
- ZIP limpio sin `.git`, `__pycache__`, DB local, logs ni ZIPs antiguos.
