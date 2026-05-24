# NeMeSiS SHARK PRO - V515 CLIENT ACCOUNT UX + ROLE CLEANUP + SPORTSDDB CREST SYNC

V515 mejora la experiencia final de cuenta cliente y separa de forma clara la zona admin.

## Incluye

- Registro con nombre visible, username, email y contrasena.
- Login con email o username.
- Migracion segura de `users.username`.
- Username normalizado y unico.
- Sesion Flask con `user_id`, `user_email`, `username`, `user_name`, `user_role` y `membership`.
- Perfil cliente limpio, sin diagnosticos ni rutas admin.
- Navegacion distinta para invitado, cliente y admin.
- Panel `/admin/users` con username, email, rol, membresia, alta y ultimo login.
- Ruta admin `/admin/sportsdb-sync`.
- API protegida `/api/sportsdb/sync-crests`.
- TheSportsDB solo bajo sync admin o `refresh=1`, no en cada carga.
- Cache SQLite para escudos y fallback SVG propio.
- Seeds de equipos reales importantes y limpieza de partidos seed ficticios.

## Variables

- `THESPORTSDB_API_KEY` o `THESPORTSDB_KEY`
- `ENABLE_LIVE_API=true`
- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `SECRET_KEY`

## Verificacion

- Registro con username.
- Login por email.
- Login por username.
- Username/email duplicados con error claro.
- Favoritos por usuario.
- Admin/users protegido.
- SportsDB sync protegido y con cache SQLite.
- ZIP limpio sin `.git`, `__pycache__`, logs ni DB local.
