# NeMeSiS SHARK PRO V517 — User Database Recovery + Admin Bootstrap Safe Access

Versión completa Render-ready con:

- Login cliente con email o username.
- Registro con nombre visible, username único, email y contraseña.
- Migración segura de `users.username` y backfill automático para usuarios antiguos.
- Acceso admin con email o username.
- Bootstrap seguro de admin inicial desde variables Render.
- Ruta `/admin-bootstrap` bloqueada automáticamente cuando ya existe un admin.
- Ruta `/admin/user-import` para importar usuarios desde `old_database.db` si existe una copia antigua.
- Conversión de contraseña en texto plano a hash cuando se importa desde DB antigua.
- Conservación de `password_hash` si la DB antigua ya lo trae.
- Panel admin con acceso a importación de usuarios.
- SQLite endurecido con DB_PATH=/data/database.db.
- Sin scraping ilegal.

## Variables Render recomendadas

```txt
ADMIN_EMAIL=tuemail@email.com
ADMIN_USERNAME=admin
ADMIN_PASSWORD=tu_contraseña_segura
ADMIN_NAME=Administrador
DB_PATH=/data/database.db
SECRET_KEY=una_clave_segura
THESPORTSDB_API_KEY=tu_key
THESPORTSDB_KEY=tu_key
ENABLE_LIVE_API=true
```

## Rutas nuevas

- `/admin-bootstrap`
- `/admin/user-import`
- `/api/admin/bootstrap-status`

## Importar usuarios antiguos

Si tienes una base antigua, súbela temporalmente como:

```txt
old_database.db
```

en la raíz del proyecto y entra como ADMIN a:

```txt
/admin/user-import
```

No se muestran contraseñas ni hashes completos.

## QA realizado

- `app.py` compila.
- `/api/health` responde.
- Registro con username probado.
- Login con username probado.
- Login con email probado.
- Login admin con username probado.
- `/admin/users` probado.
- `/admin/user-import` probado.
- `/api/admin/bootstrap-status` probado.
