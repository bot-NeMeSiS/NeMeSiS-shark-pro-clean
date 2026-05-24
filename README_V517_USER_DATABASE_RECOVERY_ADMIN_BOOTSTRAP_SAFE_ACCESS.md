# NeMeSiS SHARK PRO - V517 USER DATABASE RECOVERY + ADMIN BOOTSTRAP SAFE ACCESS

V517 protege el acceso admin y añade recuperacion segura de usuarios desde bases antiguas.

## Incluye

- Bootstrap admin automatico si no existe ningun ADMIN y estan configuradas las variables Render.
- Ruta temporal `/admin-bootstrap`, bloqueada automaticamente cuando ya existe un ADMIN.
- `/admin-login` permite email o username.
- `/admin/user-import` protegido para importar usuarios desde `old_database.db`.
- Compatibilidad con tablas antiguas `users`, `clientes`, `clients` y `usuarios`.
- Compatibilidad de columnas: email/correo, password_hash/password, name/nombre, username/user, role/rol y membership/membresia.
- Password en texto plano de DB antigua se convierte a hash antes de guardar.
- No sobrescribe usuarios existentes si el email ya esta registrado.
- Genera usernames faltantes desde email con sufijo seguro si hay duplicados.

## Variables Render

- `ADMIN_EMAIL`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `ADMIN_NAME`

## Seguridad

- No se guardan contrasenas en texto plano.
- No se muestran hashes.
- No se exponen variables Render.
- Importacion solo disponible para ADMIN.
