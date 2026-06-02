# V609 — Render Startup Repair

## Problema corregido
Render estaba matando el worker durante `init_db()` al ejecutar `cleanup_fake_matches(cur)`.
La limpieza cargaba todos los partidos en memoria y podía provocar timeout/pantalla 500 en arranque.

## Cambios
- `cleanup_fake_matches()` ahora es segura y no bloquea el arranque.
- Por defecto no se ejecuta en producción.
- Si se quiere usar manualmente, activar `CLEANUP_FAKE_MATCHES_ON_STARTUP=true`.
- La limpieza usa SQL directo, sin `fetchall()` masivo.
- Se valida que existan columnas antes de ejecutar.

## Recomendación Render
No añadas `CLEANUP_FAKE_MATCHES_ON_STARTUP=true` salvo mantenimiento puntual.
