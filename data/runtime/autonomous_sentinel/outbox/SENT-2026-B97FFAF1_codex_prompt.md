Corrige esta incidencia en NeMeSiS SHARK PRO sin romper nada anterior.

ID:
SENT-2026-B97FFAF1

Area:
render

Severidad:
high

Problema:
Render runtime no consultado en este scan

Ruta afectada:
Sin ruta concreta

Archivo probable:
Por determinar

Evidencia:
El worker no hace llamadas externas por defecto.

Impacto:
Afecta a claridad, operacion o confianza del producto si permanece activo.

Reglas:

* No inventar datos.
* No tocar secretos.
* No romper usuarios, sesiones, membresias, pagos, DB_PATH, Madrid Time, Render Cron ni Telegram dedupe.
* Mantener navegacion cliente/admin separada.
* Mantener estados seguros si faltan datos reales.

Que debes hacer:
Consultar /api/runtime-version durante QA de despliegue.

Validaciones obligatorias:
* python -m py_compile app.py
* python tools/run_continuous_sentinel_static.py

Entrega:

* resumen de cambios;
* archivos tocados;
* validaciones pasadas;
* limitaciones honestas;
* ZIP limpio si corresponde.