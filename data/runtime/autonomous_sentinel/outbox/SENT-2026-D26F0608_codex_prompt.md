Corrige esta incidencia en NeMeSiS SHARK PRO sin romper nada anterior.

ID:
SENT-2026-D26F0608

Area:
telegram

Severidad:
info

Problema:
Telegram no configurado

Ruta afectada:
Sin ruta concreta

Archivo probable:
Por determinar

Evidencia:
Runtime no confirma Telegram configurado.

Impacto:
Afecta a claridad, operacion o confianza del producto si permanece activo.

Reglas:

* No inventar datos.
* No tocar secretos.
* No romper usuarios, sesiones, membresias, pagos, DB_PATH, Madrid Time, Render Cron ni Telegram dedupe.
* Mantener navegacion cliente/admin separada.
* Mantener estados seguros si faltan datos reales.

Que debes hacer:
Mostrar estado No configurado y no prometer envios reales.

Validaciones obligatorias:
* python -m py_compile app.py
* python tools/run_continuous_sentinel_static.py

Entrega:

* resumen de cambios;
* archivos tocados;
* validaciones pasadas;
* limitaciones honestas;
* ZIP limpio si corresponde.