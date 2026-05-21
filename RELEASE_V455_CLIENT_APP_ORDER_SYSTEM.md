# NeMeSiS SHARK PRO — V455 CLIENT APP ORDER SYSTEM

Objetivo: ordenar la experiencia cliente para que la app deje de sentirse como un panel mezclado y empiece como una app deportiva viva.

Incluye:
- Portada pública/cliente centrada en partidos de hoy.
- Navegación única: Inicio, Partidos, Live, Picks, Cuenta.
- Rutas nuevas: `/partidos`, `/en-directo`, `/picks`, `/match/<id>` y `/partido/<id>`.
- Fallback premium de escudos con iniciales limpias, sin `N/A` visual.
- Estado vacío correcto para picks cuando no hay picks activos.
- Detalle de partido preparado para resumen, picks y live.
- Sobrescritura de `/` y `/app` hacia la nueva experiencia ordenada.
- Validación Python: `app.py` compila correctamente.

Pendiente para siguiente fase:
- Arreglar origen real de picks si no aparecen desde base de datos/admin.
- Revisar Telegram delivery después de ordenar cliente.
- Conectar eventos live reales al timeline.
