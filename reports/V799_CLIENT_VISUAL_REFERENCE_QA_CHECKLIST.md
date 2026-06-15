# V799 Client Visual Reference QA Checklist

## Comprobar tras subir a Render
1. `/api/runtime-version` muestra V799_REFERENCE_SCREEN_VISUAL_POLISH_APP_LIKE_FINAL.
2. Login cliente y abrir `/app`.
3. Verificar sidebar PC: Inicio, Partidos, Directo, Picks, SHARK, Histórico, Telegram, Cuenta y Salir.
4. Verificar móvil: bottom nav Inicio, Partidos, Directo, Picks, SHARK y píldoras Cuenta/Cerrar sesión.
5. `/calendar?lane=today`: partidos reales, hora Madrid, escudos/fallback, detalle y SHARK.
6. `/live`: si hay directo, marcador/minuto; si no hay, estado vacío bonito.
7. `/picks`: solo picks reales; sin cuotas, stake o riesgos inventados.
8. `/match/<id>`: hero, datos reales, pick conectado si existe, SHARK y estado de disponibilidad.
9. `/mi-cuenta`: plan, favoritos, actividad, Telegram, pagos y cerrar sesión.
10. `/telegram`: vinculación y código sin ejemplos falsos.

## Regla de producto
Si una pantalla no tiene datos reales sincronizados, debe verse premium igualmente, pero indicar pendiente/sin datos reales en vez de inventar.
