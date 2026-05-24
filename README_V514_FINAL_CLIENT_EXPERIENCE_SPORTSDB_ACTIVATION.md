# NeMeSiS SHARK PRO - V514 FINAL CLIENT EXPERIENCE & SPORTSDDB ACTIVATION

V514 deja la experiencia de cliente lista para uso real sobre V513, sin rehacer arquitectura.

## Incluye

- Perfil cliente ampliado con nombre, email, rol, membresia, favoritos, live, picks y accesos rapidos.
- Favoritos asociados a `user_id`.
- Migracion segura para `favorites.user_id`.
- APIs de favoritos por usuario.
- Gating visual para FREE, PRO, ELITE y ADMIN.
- Panel `/admin/users` protegido para ver usuarios y cambiar membresia.
- `/admin/import-center` y APIs de importacion siguen protegidas.
- Diagnostico `/api/thesportsdb/diagnostics`.
- TheSportsDB con clave enmascarada, estado live API, prueba de resolucion y ultimo error.
- Escudos persistentes: API permitida, cache SQLite y fallback SVG propio.

## Variables

- `THESPORTSDB_API_KEY` o `THESPORTSDB_KEY`
- `ENABLE_LIVE_API=true`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `SECRET_KEY`

## Verificacion

- `app.py` compila.
- Engines compilan.
- Registro/login/logout probados.
- Favoritos por usuario probados.
- Admin users probado.
- Diagnostico TheSportsDB probado sin exponer key.
- ZIP limpio sin `.git`, `__pycache__`, logs ni DB local.
