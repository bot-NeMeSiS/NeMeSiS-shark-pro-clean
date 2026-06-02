# V586 — Telegram Picks Premium por Membresía + Escudos

## Objetivo

Enviar picks por Telegram con segmentación real FREE / PRO / ELITE / ADMIN y formato premium adaptado al plan.

## Implementado

- Nuevas funciones de formato:
  - `format_telegram_pick_free(pick)`
  - `format_telegram_pick_pro(pick)`
  - `format_telegram_pick_elite(pick)`
- Filtro por membresía:
  - FREE recibe solo picks FREE y formato resumido.
  - PRO recibe FREE + PRO con cuota, confianza, riesgo, stake y motivo.
  - ELITE recibe todo con value, explicación SHARK, learning y precaución.
  - ADMIN puede recibir todo como destino interno.
- El resumen diario de picks se construye por destinatario y por plan.
- Los picks publicados individuales también se segmentan por plan antes de entrar en `telegram_queue`.
- Auditoría `/admin/telegram-audit` ampliada con:
  - destinatarios FREE / PRO / ELITE
  - picks enviables por plan
  - bloqueados por membresía
  - errores/fallback de escudos
  - mensajes solo texto
  - mensajes con imagen preparados como métrica futura
- Escudos:
  - Se detectan `home_logo`, `away_logo`, `team_badge` y `league_badge`.
  - Si no hay escudo, no se rompe el envío: se usa texto premium.
  - La cola guarda contexto de badge/fallback en `payload`.
- Logs:
  - `[TELEGRAM_PLAN]`
  - `[TELEGRAM_FORMAT]`
  - `[TELEGRAM_BADGES]`
  - `[MEMBERSHIP_FILTER]`

## Pruebas

- `compileall app.py engines`: OK.
- Prueba de formato:
  - FREE no recibe un pick PRO.
  - PRO recibe stake sugerido.
  - ELITE recibe explicación de learning.

## Notas

- No se cambia el envío HTTP existente ni el test de Telegram.
- No se rompe `telegram_queue`: solo se mejora el cuerpo y payload que entran a la cola.
- El envío con imagen queda preparado como métrica/contexto, pero el canal operativo sigue usando texto premium para mantener compatibilidad y fiabilidad.

