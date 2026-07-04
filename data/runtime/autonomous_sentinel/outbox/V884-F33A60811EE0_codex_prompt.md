Corrige esta incidencia en NeMeSiS SHARK PRO sin romper nada anterior.

ID:
V884-F33A60811EE0

Area:
data

Severidad:
low

Problema:
Pantalla deportiva sin datos reales visibles

Ruta afectada:
/calendar

Archivo probable:
Por determinar

Evidencia:
Hay estado seguro, pero no hay filas/cards deportivas reales visibles.

Impacto:
Afecta a claridad, operacion o confianza del producto si permanece activo.

Reglas:

* No inventar datos.
* No tocar secretos.
* No romper usuarios, sesiones, membresias, pagos, DB_PATH, Madrid Time, Render Cron ni Telegram dedupe.
* Mantener navegacion cliente/admin separada.
* Mantener estados seguros si faltan datos reales.

Que debes hacer:
Mantener el estado seguro y crear tarea admin de sync/filtros/cache.

Validaciones obligatorias:
* python -m py_compile app.py
* python tools/run_continuous_sentinel_static.py

Entrega:

* resumen de cambios;
* archivos tocados;
* validaciones pasadas;
* limitaciones honestas;
* ZIP limpio si corresponde.