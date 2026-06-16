# V804 Client Live Tracker QA Checklist

Después de desplegar en Render:

1. Confirmar `/api/runtime-version` muestra V804.
2. Confirmar que `API_FOOTBALL_KEY` está configurada en Render.
3. Confirmar `ENABLE_API_FOOTBALL_PROVIDER=true`.
4. Confirmar `ENABLE_API_FOOTBALL_LIVE_TRACKER=true`.
5. Abrir `/live` durante partidos en directo.
6. Ver que el proveedor muestra API-Football Pro activo.
7. Comprobar que las cards live enlazan a `/match/af-<fixture_id>`.
8. Abrir un partido live y pulsar “Actualizar tracker”.
9. Ver eventos reales si API-Football los devuelve.
10. Ver comparativa de estadísticas si API-Football las devuelve.
11. Confirmar que si no hay balón exacto aparece “no se inventa”.
12. Confirmar que no hay números inventados en pantallas sin datos.
