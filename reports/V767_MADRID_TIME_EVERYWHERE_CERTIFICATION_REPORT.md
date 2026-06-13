# V767 Madrid Time Everywhere Certification

## Objetivo
Garantizar que todo horario visible para cliente y admin se muestre siempre en hora oficial de España, zona `Europe/Madrid`, sin excepciones.

## Cambios aplicados
- Reforzado `engines/madrid_time_engine.py` para distinguir entre timestamps de API con UTC/offset y valores manuales/DB `match_date + kickoff_time` ya escritos en hora Madrid.
- Añadido parseo local Madrid para evitar doble desplazamiento: un partido manual a las 21:30 se queda a las 21:30 Madrid, no pasa a 23:30.
- Reforzada `spanish_localization_engine.py` para respetar valores ingenuos como hora Madrid cuando vienen de admin/DB.
- Nuevos filtros estrictos: `match_madrid_datetime` y `match_madrid_context`.
- Actualizadas pantallas admin y cliente que todavía mostraban campos crudos como `match_date`, `display_datetime` o `safe_datetime`.
- Los textos visibles usan etiquetas de cliente/admin con Madrid como fuente única.

## Alcance
Aplica a:
- Home cliente.
- Calendario.
- Live/directo.
- Picks.
- Detalle de partido.
- Mundial/modo dinámico.
- Resúmenes/highlights.
- Admin de picks, inteligencia, live depth y diagnósticos.
- Telegram mantiene `format_telegram_match_time_madrid()`.

## No se tocó
- Telegram automático.
- Cron Render.
- `tools/render_cron_telegram_tick.py`.
- `/api/automation/telegram/tick`.
- `AUTOMATION_SECRET`.
- `DB_PATH`.
- Usuarios/sesiones/membresías/pagos.

## Validación clave
- UTC verano `2026-06-12T19:00:00Z` → `21:00` Madrid.
- UTC invierno `2026-12-12T20:00:00Z` → `21:00` Madrid.
- Manual Madrid `2026-06-15 + 21:30` → `21:30` Madrid, sin doble cambio.
- Templates auditados para evitar horarios crudos visibles.

## Limitación honesta
No se puede corregir una hora que una API externa entregue ya mal etiquetada desde origen; lo que sí hace V767 es convertir correctamente UTC/offset y tratar los horarios manuales como Madrid para evitar errores internos.
