# V708 RENDER CRON GUIDE

## Variables Render obligatorias

Configurar en Render > Environment:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=-1003951459919
TELEGRAM_BOT_USERNAME=nemesi_shark_pro_bot
ENABLE_TELEGRAM_AUTO=true
AUTO_SEND_TELEGRAM_PICKS=true
AUTO_GENERATE_PICKS=true
SCHEDULER_ENABLED=true
DAILY_AUTOMATION_ENABLED=true
RUN_DAILY_AUTOMATION=true
RUN_STARTUP_SCHEDULER_NOW=0
AUTOMATION_SECRET=un_secreto_largo_y_privado
MIN_SHARK_SCORE_FOR_AUTO_SEND=78
MAX_AUTO_PICKS_PER_DAY=3
```

Tambien mantener:

```env
DB_PATH=/data/database.db
THESPORTSDB_KEY=...
THE_ODDS_API_KEY=...
ENABLE_ODDS_API=true
ENABLE_LIVE_API=true
```

## Cron recomendado

### 1. Daily automation

Frecuencia:

- Cada dia a las 10:00 Europe/Madrid
- Opcionalmente cada hora durante horario deportivo si se quiere mas actividad

Metodo:

`GET`

URL:

```text
https://TU-SERVICIO.onrender.com/api/automation/daily/run?secret=AUTOMATION_SECRET
```

Hace:

- sincroniza calendario/live/cuotas si toca
- genera recomendaciones
- genera auto picks
- encola Telegram
- procesa cola
- registra diagnostico

### 2. Telegram tick

Frecuencia:

- Cada 15 minutos

Metodo:

`GET`

URL:

```text
https://TU-SERVICIO.onrender.com/api/automation/telegram/tick?secret=AUTOMATION_SECRET
```

Hace:

- revisa picks automaticos elegibles
- encola canal global
- encola privados si existen
- procesa cola
- evita duplicados

## Seguridad

Los endpoints responden `403` si falta `AUTOMATION_SECRET` o si el secret no coincide.

Tambien pueden ejecutarse desde sesion admin, pero produccion debe usar Render Cron.

## Como comprobar produccion

1. Abrir `/admin/telegram/diagnostics`.
2. Revisar `automatic_status`.
3. Revisar `automatic_reason`.
4. Confirmar:
   - `TELEGRAM_BOT_TOKEN=true`
   - `TELEGRAM_CHAT_ID=true`
   - `ENABLE_TELEGRAM_AUTO=true`
   - `AUTO_SEND_TELEGRAM_PICKS=true`
   - `AUTOMATION_SECRET=true`
5. Mirar ultimo `last_daily_automation`.
6. Mirar ultimo `last_scheduler_tick`.
7. Mirar `last_auto_pick`.
8. Mirar `pending=0`.
9. Mirar `sent_today>0`.

