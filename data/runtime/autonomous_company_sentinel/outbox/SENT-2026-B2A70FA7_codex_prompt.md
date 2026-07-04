Corrige esta incidencia en NeMeSiS SHARK PRO sin romper nada anterior.

ID:
SENT-2026-B2A70FA7

Area:
admin

Severidad:
medium

Problema:
Navegacion cliente aparece en admin

Ruta afectada:
/admin-login

Archivo probable:
Por determinar

Evidencia:
bottom nav/sidebar/floating SHARK detectado en admin

Impacto:
Puede degradar experiencia cliente/admin o generar falsa confianza operativa.

Reglas:

* No inventar datos.
* No tocar secretos.
* No romper usuarios, sesiones, membresias, pagos, DB_PATH, Madrid Time, Render Cron ni Telegram dedupe.
* Mantener navegacion cliente/admin separada.
* Mantener estados seguros si faltan datos reales.

Que debes hacer:
Revisar la causa real, corregir de forma segura y revalidar con Sentinel.

Validaciones obligatorias:
* python -m py_compile app.py
* python tools/run_continuous_sentinel_static.py

Entrega:

* resumen de cambios;
* archivos tocados;
* validaciones pasadas;
* limitaciones honestas;
* ZIP limpio si corresponde.