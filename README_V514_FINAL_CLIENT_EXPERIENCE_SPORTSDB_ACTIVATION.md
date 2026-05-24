# NeMeSiS SHARK PRO — V514 FINAL CLIENT EXPERIENCE + SPORTSDDB ACTIVATION

Versión preparada sobre V513 para dejar la experiencia de cliente conectada y lista para Render.

## Incluye

- Login/registro V513 mantenido.
- Perfil cliente mejorado.
- Favoritos por usuario (`user_id`).
- Panel admin `/admin/users` para ver usuarios y cambiar membresía.
- Protección admin mantenida en `/admin/import-center`.
- Diagnóstico TheSportsDB en `/api/thesportsdb/diagnostics`.
- TheSportsDB key detectada desde `THESPORTSDB_API_KEY` o `THESPORTSDB_KEY`.
- Escudos por TheSportsDB + cache SQLite + fallback SVG premium.
- Navegación cliente mejorada.
- V514 health en `/v514-health`.
- SQLite con migraciones seguras, sin pedir borrar DB manualmente.

## Rutas principales probadas por diseño

- `/`
- `/registro`
- `/cliente-login`
- `/admin-login`
- `/logout`
- `/perfil`
- `/profile`
- `/match-hub`
- `/live`
- `/picks`
- `/combis`
- `/favorites`
- `/shark`
- `/telegram`
- `/escudos`
- `/admin/import-center`
- `/admin/users`
- `/api/health`
- `/api/profile`
- `/api/favorites`
- `/api/thesportsdb/diagnostics`

## Variables Render recomendadas

```txt
DB_PATH=/data/database.db
SECRET_KEY=...
THESPORTSDB_API_KEY=tu_key
THESPORTSDB_KEY=tu_key
ENABLE_LIVE_API=true
ADMIN_EMAIL=tu_email_admin
ADMIN_PASSWORD=tu_password_admin
```

## Legalidad

Sin scraping ilegal. TheSportsDB se usa como API permitida y la app mantiene fallback visual propio.
