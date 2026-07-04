Corrige esta incidencia en NeMeSiS SHARK PRO sin romper nada anterior.

ID:
SENT-2026-A5A55C7D

Area:
logos

Severidad:
medium

Problema:
Cache de logos en cero con fallback obligatorio

Ruta afectada:
/partidos

Archivo probable:
Por determinar

Evidencia:
team_logo_cache_count=0 y league_logo_cache_count=0

Impacto:
Las cards deportivas deben usar fallback premium sin imagen rota ni escudo inventado.

Reglas:

* No inventar datos.
* No tocar secretos.
* No romper usuarios, sesiones, membresias, pagos, DB_PATH, Madrid Time, Render Cron ni Telegram dedupe.
* Mantener navegacion cliente/admin separada.
* Mantener estados seguros si faltan datos reales.

Que debes hacer:
Verificar fallback visual y documentar sincronizacion segura si procede.

Validaciones obligatorias:
* Smoke /partidos
* Smoke /live
* Smoke /picks

Entrega:

* resumen de cambios;
* archivos tocados;
* validaciones pasadas;
* limitaciones honestas;
* ZIP limpio si corresponde.