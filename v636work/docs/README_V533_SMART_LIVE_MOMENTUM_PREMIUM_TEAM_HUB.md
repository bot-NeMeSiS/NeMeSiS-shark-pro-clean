# NeMeSiS SHARK PRO — V533 Smart Live Momentum + Premium Team Hub

Build completa Render-ready basada en la última base estable V532.

Incluye:
- Live Center agrupado por ligas.
- Momentum visual y estados premium para partidos live/próximos/finalizados.
- Páginas de equipo `/team/<id>` con próximos partidos, últimos resultados, favoritos y contexto SHARK.
- Detalle de partido `/match/<id>` enlazado con equipos, picks y favoritos.
- Favoritos inteligentes por equipo/liga/partido.
- Separación cliente/admin mantenida.
- Login, perfil, picks, combis, calendario, resultados y rutas principales conservadas.
- ZIP limpio sin `.git`, DB local, logs, `__pycache__` ni ZIPs antiguos.

QA local:
- `app.py` compila correctamente.
- Estructura normalizada para Render/Linux.

Tras subir a Render, probar:
- `/api/health`
- `/cliente-login`
- `/perfil`
- `/match-hub`
- `/live`
- `/picks`
- `/combis`
- `/favorites`
- `/match/1`
- `/team/1`
