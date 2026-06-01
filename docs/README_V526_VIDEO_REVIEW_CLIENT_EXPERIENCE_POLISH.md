# NeMeSiS SHARK PRO V526 — Video Review Client Experience Polish

Build basada en V524 revisada con el vídeo del flujo real.

## Cambios principales

- Favoritos con opción de quitar/cancelar desde la propia pantalla cliente.
- Feed de favoritos conectado a equipos, ligas y partidos guardados.
- Información resumida de favoritos: equipos, ligas, partidos y coincidencias.
- SHARK IA flotante animado para cliente, conectado a `/api/shark/ask`.
- Botón SHARK IA añadido a navegación cliente.
- Landing inicial diferenciada del dashboard cliente.
- Landing con membresías FREE / PRO / ELITE y propuesta comercial clara.
- Perfil cliente limpiado: elimina métricas técnicas como escudos guardados.
- `/escudos` protegido para admin, no visible como servicio cliente.
- Añadida ruta visual `/match/<match_id>` y `/partido/<match_id>` para detalle de partido.
- Mantiene V524: resultados, picks, combis, calendario por día/liga y estados de partido.

## QA técnico

- `app.py` compila correctamente.
- ZIP limpio sin `.git`, `__pycache__`, DB local, logs ni ZIPs antiguos.
- Render-ready.
