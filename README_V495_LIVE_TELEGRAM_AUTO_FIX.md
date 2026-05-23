# NeMeSiS SHARK PRO — V495 LIVE + TELEGRAM AUTO FIX

Base: V494 GLOBAL FOOTBALL STRUCTURE SYSTEM

Cambios incluidos:
- Corrige fallo de sintaxis final en app.py que impedía arrancar.
- Actualiza APP_VERSION a V495.
- Nuevo puente live real normalizado:
  - /api/v495/live-real
  - /api/v495/live-diagnostics
- Normaliza marcador, minuto, estado, liga, eventos y escudos cuando existan.
- Añade scheduler runtime ligero para Render:
  - ejecuta Telegram automático con tráfico real
  - evita duplicados usando SQLite persistente
  - configurable por variables
- Nuevo endpoint manual:
  - /api/v495/telegram-auto-run?force=1
- Nuevo endpoint de estado:
  - /api/v495/automation-status
- Nuevo health:
  - /v495-health

Variables nuevas opcionales:
ENABLE_TELEGRAM_AUTO=true
TELEGRAM_AUTO_MINUTES=360
TELEGRAM_AUTO_START_HOUR=10
TELEGRAM_AUTO_END_HOUR=23

Importante:
- No se inventan lives: si la API no devuelve minuto/marcador real, el diagnóstico lo indica.
- El scheduler runtime funciona con tráfico; para producción avanzada puede combinarse con cron externo llamando a /api/v495/telegram-auto-run?force=1.
