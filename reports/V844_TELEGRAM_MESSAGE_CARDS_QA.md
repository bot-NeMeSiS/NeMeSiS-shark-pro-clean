# V844 Telegram Message Cards QA

## Estado
El formateador principal ya construye tarjetas premium para picks y resúmenes. V844 no reescribe todo el formato; evita que llegue basura a esas tarjetas.

## Reglas validadas
- Mensaje premium en español.
- Incluye SHARK, partido, competición, hora Madrid, mercado y cuota si existe.
- No inventa cuota si no existe.
- No contiene mojibake visible en el check de tarjeta.
- No envía contenido vacío si no hay pick real.

## Resultado
	ools/check_v844_telegram_message_cards.py pasa correctamente.
