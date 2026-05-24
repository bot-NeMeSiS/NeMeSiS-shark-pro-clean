# NeMeSiS SHARK PRO - V513 CLIENT ACCESS & MEMBERSHIP LOGIN SYSTEM

V513 consolida el acceso real de clientes sin rehacer V512.

## Incluye

- Registro cliente en `/registro`.
- Login cliente en `/cliente-login`.
- Login admin discreto en `/admin-login`.
- Logout en `/logout`.
- Sesiones Flask con `user_id`, `user_email`, `user_role`, `user_name` y `user_membership`.
- Tabla `users` en SQLite con migración segura.
- Contraseñas con hash de Werkzeug.
- Perfil conectado al usuario autenticado.
- `/admin/import-center` protegido para rol `ADMIN`.
- APIs de importación protegidas para admin.
- Navegación adaptada a sesión: Entrar, Crear cuenta, Mi perfil y Salir.

## Admin

El acceso admin puede usar un usuario con rol `ADMIN` existente o estas variables de entorno:

- `ADMIN_EMAIL`
- `ADMIN_PASSWORD`
- `ADMIN_NAME` opcional

No se incluye una contraseña admin fija en el código.

## Verificación

- `app.py` compila.
- Engines compilan.
- Registro, login, logout y protección admin probados con SQLite temporal.
- ZIP limpio sin `.git`, `__pycache__`, logs ni DB local.
