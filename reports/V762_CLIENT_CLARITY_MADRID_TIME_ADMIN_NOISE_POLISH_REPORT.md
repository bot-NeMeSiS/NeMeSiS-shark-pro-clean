# V762_CLIENT_CLARITY_MADRID_TIME_ADMIN_NOISE_POLISH

## Objetivo
Pulir la experiencia cliente para que cada pantalla sea entendible, ordenada y vendible: partidos con día y hora Madrid, picks con partido completo, menos ruido interno y sin textos de admin en vistas de usuario.

## Cambios principales
- Añadidos helpers cliente en `app.py` para generar etiquetas seguras de partido: equipos, competición, día, fecha, hora Madrid, estado y resultado.
- Añadido enriquecimiento de picks con contexto de partido cuando existe `match_id`.
- Home cliente ahora muestra partidos con día + hora Madrid + competición + estado/resultado.
- Home cliente ahora muestra picks activos con partido completo, mercado, selección, cuota y riesgo.
- Calendario reforzado con fecha/hora Madrid y mensajes no técnicos.
- Live reforzado para diferenciar directo, finalizados y próximos con fecha/hora Madrid.
- Detalle de partido muestra día y hora Madrid completos.
- Se han retirado/ocultado strips internos de versión y lenguaje técnico de vistas cliente clave.
- CSS V762 añade filas compactas, legibles y responsive para partido/pick.

## Conservado
- Telegram automático y lógica V755.
- Cron Render y `/api/automation/telegram/tick`.
- `tools/render_cron_telegram_tick.py`.
- `AUTOMATION_SECRET`.
- `DB_PATH`.
- usuarios, sesiones, membresías y pagos reales.
- Madrid Time.

## Limitaciones
- No se ejecutó envío real a Telegram.
- El entorno sandbox no tiene Flask instalado, así que no se pudo hacer smoke Flask real local.
- La calidad de datos reales depende de Render, APIs y base persistente.
