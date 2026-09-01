Corrige esta incidencia en NeMeSiS SHARK PRO sin romper nada anterior.

ID:
SENT-2026-F5D25D28

Area:
sentinel

Severidad:
critical

Problema:
Enlace interno roto

Ruta afectada:
/app

Archivo probable:
Por determinar

Evidencia:
Clic real desde Home termina en una ruta 404.

Impacto:
Afecta a claridad, operacion o confianza del producto si permanece activo.

Reglas:

* No inventar datos.
* No tocar secretos.
* No romper usuarios, sesiones, membresias, pagos, DB_PATH, Madrid Time, Render Cron ni Telegram dedupe.
* Mantener navegacion cliente/admin separada.
* Mantener estados seguros si faltan datos reales.

Que debes hacer:
Revisar causa real y corregir sin tocar secretos ni datos reales.

Validaciones obligatorias:
* python -m py_compile app.py
* python tools/run_continuous_sentinel_static.py

Entrega:

* resumen de cambios;
* archivos tocados;
* validaciones pasadas;
* limitaciones honestas;
* ZIP limpio si corresponde.