Corrige esta incidencia en NeMeSiS SHARK PRO sin romper nada anterior.

ID:
SENT-2026-DC078E31

Area:
visual

Severidad:
medium

Problema:
No hay imagenes de referencia locales

Ruta afectada:
reference_images

Archivo probable:
Por determinar

Evidencia:
REFERENCE_IMAGES_MISSING

Impacto:
La comparacion visual queda limitada a reglas estaticas y no a fotos reales.

Reglas:

* No inventar datos.
* No tocar secretos.
* No romper usuarios, sesiones, membresias, pagos, DB_PATH, Madrid Time, Render Cron ni Telegram dedupe.
* Mantener navegacion cliente/admin separada.
* Mantener estados seguros si faltan datos reales.

Que debes hacer:
Anadir referencias en reports/reference_images o docs/reference_ui.

Validaciones obligatorias:
* Verificar carpeta de referencias

Entrega:

* resumen de cambios;
* archivos tocados;
* validaciones pasadas;
* limitaciones honestas;
* ZIP limpio si corresponde.