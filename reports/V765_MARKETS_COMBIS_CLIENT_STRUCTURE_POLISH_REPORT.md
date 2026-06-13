# V765_MARKETS_COMBIS_CLIENT_STRUCTURE_POLISH

## Objetivo
Añadir valor comercial sin desordenar la app: mercados básicos entendibles, combis responsables y revisión de enlaces/ruido visual en pantallas cliente.

## Añadido
- Nueva guía cliente de mercados: `/mercados`, `/markets`, `/apuestas-basicas`.
- Nueva API cliente: `/api/client/betting-markets`.
- Nuevo motor: `engines/betting_markets_engine.py`.
- Catálogo básico: 1X2, doble oportunidad, empate no apuesta, +1.5/+2.5 goles y ambos marcan.
- Combis separadas por estrategia: 1X2 controlada, goles básica y mixta responsable.
- Las combis solo usan picks reales publicados con mercado, cuota y confianza suficiente.
- Si faltan mercado/cuota/contexto, la app muestra aviso y no vende la señal como pick completo.

## Pantallas reforzadas
- Home: acceso a Mercados y Combis, bloque de mercados claros.
- Picks: bloque “Mercado antes que pick”.
- Calendario/Live: orden de lectura para no perder contexto.
- Detalle de partido: guía de mercados básicos del partido.
- Combis: pantalla reestructurada, links rotos corregidos y estrategias de combi más claras.
- Menú y navegación: acceso cliente a Mercados.

## Conservado
No se tocó Telegram automático, Cron de Render, `tools/render_cron_telegram_tick.py`, `/api/automation/telegram/tick`, `AUTOMATION_SECRET`, `DB_PATH`, usuarios, sesiones, membresías, pagos reales ni Madrid Time.

## Limitación honesta
No se inventan cuotas ni picks. Si la fuente real no trae mercado/cuota, la app explica que está pendiente.
