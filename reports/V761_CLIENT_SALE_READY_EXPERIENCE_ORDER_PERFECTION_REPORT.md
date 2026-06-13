# V761_CLIENT_SALE_READY_EXPERIENCE_ORDER_PERFECTION

## Objetivo
Corregir el desorden visible en vídeo después de V759/V760 y dejar la experiencia cliente más cercana a modo venta: menos ruido, navegación clara, SHARK usable, calendario/live con día y resultado claros, picks más fáciles de entender y menú cliente más ordenado.

## Cambios aplicados
- Se mantiene V755/V759/V760: Telegram, Cron, DB_PATH, usuarios, sesiones, Madrid Time y normalización de candidatos no se tocan.
- Navegación cliente simplificada: SHARK queda visible y los accesos técnicos PC/Móvil no aparecen como ruido en el home.
- Bottom nav se oculta en PC y se conserva en móvil para evitar doble navegación visual.
- SHARK widget gana fallback GET si el POST falla por sesión/CSRF, mensaje de error más claro y estado visual de panel abierto.
- Se elimina el enlace roto `/sharkmatch=` en detalle de partido y pasa a `/shark?match=...`.
- Home cliente añade flujo de uso: Partidos → Picks → SHARK → Histórico.
- Picks añade flujo de lectura: qué apostar → cuota/stake → riesgo → resultado.
- Calendario ahora muestra fecha, hora, estado y resultado/estado final dentro de cada tarjeta.
- Live ahora muestra día, hora, marcador/estado y diferencia finalizado/directo/próximo de forma clara.
- Menú cliente reorganizado para venta: Inicio, Calendario, Directo, Picks, Histórico, SHARK, Telegram, Cuenta, Ayuda y Legal.

## No tocado
- `tools/render_cron_telegram_tick.py`.
- `/api/automation/telegram/tick`.
- `AUTOMATION_SECRET`.
- `DB_PATH`.
- Secretos reales.
- Envío Telegram real.
- Pagos reales.
- Datos de usuarios/membresías.

## Validación esperada
- `python -m py_compile app.py`.
- `python -m compileall app.py engines tools`.
- `python tools/check_v761_client_sale_ready_experience_order.py`.
- Build limpio con `tools/build_clean_release.py`.
- ZIP audit con `forbidden_count=0`.

## Limitación honesta
Esta versión ordena la experiencia y arregla fallos visibles, pero los datos reales de partidos, picks, escudos y Telegram dependen de Render, APIs y base persistente real. No se envía Telegram real desde sandbox.
