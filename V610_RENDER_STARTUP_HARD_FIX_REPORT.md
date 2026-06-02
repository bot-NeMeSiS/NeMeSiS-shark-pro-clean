# V610 — Render Startup Hard Fix

## Problema
Render seguía abortando el worker dentro de `cleanup_fake_matches()` durante `init_db()`.

## Solución
- `cleanup_fake_matches()` queda como función de compatibilidad que retorna inmediatamente.
- Se elimina su ejecución durante `init_db()`.
- La limpieza demo ya no puede bloquear el primer HEAD/GET de Render.
- Mantiene intacto login, Telegram, SHARK, warehouse y rutas principales.

## Validación
- `compileall` OK.
- Import de `app` OK con `SECRET_KEY` y DB temporal.
- `seed_core()` OK con DB temporal.

## Nota
Si en el futuro se quiere limpiar datos demo, debe hacerse desde endpoint/tarea admin separada y paginada, no en arranque.
