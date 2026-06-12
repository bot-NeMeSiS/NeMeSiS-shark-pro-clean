# CHATGPT CONTINUATION REPORT

## Estado actual

NeMeSiS SHARK PRO continúa desde `V727_TELEGRAM_RELIABILITY_COMMAND_CENTER`.

La base anterior era `V726_TOTAL_PROJECT_CLEANUP_LIVE_EXPERIENCE_ORGANIZATION`, con Live/Calendar más compactos, release limpio y cron protegido.

## Problema que motivó V727

Telegram no enviaba desde las 12:00 en producción. El envío manual ya había funcionado en versiones previas, por lo que el problema probable no era el bot ni el canal, sino algún punto del flujo automático:

- Cron no llama;
- Cron llama pero no hay candidatos;
- picks descartados;
- horario silencioso;
- límites;
- dedupe;
- fallo API Telegram;
- configuración incompleta;
- Data Memory/DB;
- football-only bloqueando demasiado.

## Cambios V727

Se añadió un centro de mando Telegram:

- `/admin/telegram/command-center`
- `/api/admin/telegram/status`
- `/api/admin/telegram/dry-run`
- `/api/admin/telegram/preview-next`
- `POST /api/admin/telegram/test-send`

Se añadió motor:

- `engines/telegram_reliability_engine.py`

Se añadió script:

- `tools/check_telegram_reliability.py`

Se añadieron tests:

- `tests/test_v727_telegram_reliability.py`

Se añadieron informes:

- `V727_TELEGRAM_RELIABILITY_COMMAND_CENTER_REPORT.md`
- `TELEGRAM_RELIABILITY_AUDIT_V727.md`
- `TELEGRAM_RUNBOOK_V727.md`

## Qué hace el Command Center

Muestra sin secrets:

- BOT_TOKEN configurado sí/no;
- CHAT_ID configurado sí/no;
- PUBLIC_BASE_URL sí/no;
- AUTOMATION_SECRET sí/no;
- football-only activo;
- último Telegram Tick;
- último Daily Run;
- candidatos;
- descartes;
- picks premium elegibles;
- picks sin cuota;
- picks sin selección;
- duplicados/dedupe;
- límites por hora/día;
- horario silencioso;
- últimos errores;
- Data Memory Telegram;
- preview del siguiente mensaje sin enviar.

## Diagnósticos posibles

- `READY_TO_SEND`
- `NO_CANDIDATES`
- `NO_FOOTBALL_CANDIDATES`
- `NO_PREMIUM_PICKS`
- `ALL_DISCARDED_NO_ODDS`
- `ALL_DISCARDED_LOW_QUALITY`
- `ALL_ALREADY_SENT`
- `BLOCKED_BY_HOURLY_LIMIT`
- `BLOCKED_BY_DAILY_LIMIT`
- `BLOCKED_BY_QUIET_HOURS`
- `MISSING_BOT_TOKEN`
- `MISSING_CHAT_ID`
- `TELEGRAM_API_ERROR`
- `DB_ERROR`
- `DATA_MEMORY_ERROR`
- `UNKNOWN_ERROR`

Cada diagnóstico incluye explicación en castellano, qué hacer, severidad y si es fallo real o situación normal.

## Qué se puede saber localmente

En local, sin variables Render reales ni `/data/database.db`, el script puede verificar:

- rutas;
- imports;
- motor de diagnóstico;
- filtro football-only;
- formato de preview;
- ausencia de envío en dry-run;
- protección admin.

No puede determinar la causa exacta de producción desde las 12:00 sin:

- DB persistente real de Render;
- logs reales;
- `automation_state` real;
- cola real;
- variables Render reales.

## Qué debe mirarse en producción

1. Abrir `/admin/telegram/command-center`.
2. Ver estado principal.
3. Revisar último Cron.
4. Revisar candidatos y descartes.
5. Revisar límites y horario silencioso.
6. Revisar Data Memory.
7. Ejecutar dry-run.
8. Ejecutar preview.
9. Solo si procede, `POST /api/admin/telegram/test-send`.

## Estado de seguridad

- No se exponen secrets.
- No se envían pruebas automáticamente.
- El test de envío requiere admin y acción explícita.
- Los endpoints admin requieren sesión admin.
- Cron mantiene `AUTOMATION_SECRET`.
- Se conserva `DB_PATH=/data/database.db` para producción.

## Riesgos pendientes

- Confirmar causa real en Render con datos reales.
- Revisar si `auto_daily_picks` está activo en DB/settings.
- Revisar si el límite horario actual es demasiado estricto.
- Revisar si el dedupe bloquea nuevos picks por clave demasiado amplia.
- Confirmar permisos reales del bot en canal.

## Próximo paso recomendado

Desplegar V727 en Render, entrar como admin y abrir `/admin/telegram/command-center`. El estado principal debe decir exactamente por qué no se está enviando.
