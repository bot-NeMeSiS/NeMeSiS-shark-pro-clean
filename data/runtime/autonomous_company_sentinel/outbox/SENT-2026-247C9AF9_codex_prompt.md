Corrige esta incidencia en NeMeSiS SHARK PRO sin romper nada anterior.

ID:
SENT-2026-247C9AF9

Area:
buttons_routes

Severidad:
medium

Problema:
Ruta devuelve Not Found

Ruta afectada:
/admin-panel

Archivo probable:
Por determinar

Evidencia:
path=/admin-panel count=1 referrer=sin referrer

Impacto:
Puede dejar al usuario en una pantalla seca si llega desde PWA, enlace viejo o acceso directo.

Reglas:

* No inventar datos.
* No tocar secretos.
* No romper usuarios, sesiones, membresias, pagos, DB_PATH, Madrid Time, Render Cron ni Telegram dedupe.
* Mantener navegacion cliente/admin separada.
* Mantener estados seguros si faltan datos reales.

Que debes hacer:
Crear alias o corregir enlace de origen y revalidar smoke de rutas.

Validaciones obligatorias:
* python -m py_compile app.py
* python tools/check_v896_not_found_route_recovery.py

Entrega:

* resumen de cambios;
* archivos tocados;
* validaciones pasadas;
* limitaciones honestas;
* ZIP limpio si corresponde.