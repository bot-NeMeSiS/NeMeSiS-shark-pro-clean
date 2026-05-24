# NeMeSiS SHARK PRO - V516 CLIENT DASHBOARD FINAL PRO

V516 pule la experiencia final del cliente en `/perfil`.

## Incluye

- Dashboard cliente con saludo, username, email y membresia.
- Cards visuales para FREE, PRO, ELITE y ADMIN.
- Accesos rapidos a partidos, live, picks, combinadas, favoritos, Telegram y SHARK IA.
- Resumen de favoritos, picks destacados, partidos de hoy y servicios premium.
- Estados de Telegram, SportsDB y SHARK IA sin textos tecnicos para cliente.
- Limpieza de botones API/diagnostico en pantallas cliente.
- Admin conserva su menu separado.
- Login, registro, roles, favoritos por usuario y SportsDB Sync se mantienen.

## Verificacion

- `app.py` compila.
- Engines compilan.
- Login con email/username sigue funcionando.
- `/perfil` y `/profile` requieren sesion y renderizan dashboard cliente.
- Admin sigue protegido.
- ZIP limpio sin `.git`, `__pycache__`, logs ni DB local.
