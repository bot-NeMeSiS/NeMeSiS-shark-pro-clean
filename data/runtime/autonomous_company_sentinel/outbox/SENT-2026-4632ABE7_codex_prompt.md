Corrige esta incidencia en NeMeSiS SHARK PRO sin romper nada anterior.

ID:
SENT-2026-4632ABE7

Area:
visual

Severidad:
medium

Problema:
Browser capture unavailable

Ruta afectada:
browser

Archivo probable:
Por determinar

Evidencia:
BROWSER_CAPTURE_UNAVAILABLE

Impacto:
No se puede declarar pixel-perfect ni validar capturas reales en esta ejecucion.

Reglas:

* No inventar datos.
* No tocar secretos.
* No romper usuarios, sesiones, membresias, pagos, DB_PATH, Madrid Time, Render Cron ni Telegram dedupe.
* Mantener navegacion cliente/admin separada.
* Mantener estados seguros si faltan datos reales.

Que debes hacer:
Ejecutar browser QA con Playwright cuando este disponible.

Validaciones obligatorias:
* Browser QA desktop/mobile

Entrega:

* resumen de cambios;
* archivos tocados;
* validaciones pasadas;
* limitaciones honestas;
* ZIP limpio si corresponde.