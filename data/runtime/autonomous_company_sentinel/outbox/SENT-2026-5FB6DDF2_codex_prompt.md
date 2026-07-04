Corrige esta incidencia en NeMeSiS SHARK PRO sin romper nada anterior.

ID:
SENT-2026-5FB6DDF2

Area:
shark

Severidad:
medium

Problema:
SHARK IA avanzada pendiente de configuracion

Ruta afectada:
/shark

Archivo probable:
Por determinar

Evidencia:
openai_configured=false

Impacto:
El cliente debe ver modo seguro activo y analisis limitado sin proveedor IA.

Reglas:

* No inventar datos.
* No tocar secretos.
* No romper usuarios, sesiones, membresias, pagos, DB_PATH, Madrid Time, Render Cron ni Telegram dedupe.
* Mantener navegacion cliente/admin separada.
* Mantener estados seguros si faltan datos reales.

Que debes hacer:
Mantener copy honesto de modo seguro sin prometer OpenAI real.

Validaciones obligatorias:
* GET /api/runtime-version
* Smoke /shark

Entrega:

* resumen de cambios;
* archivos tocados;
* validaciones pasadas;
* limitaciones honestas;
* ZIP limpio si corresponde.