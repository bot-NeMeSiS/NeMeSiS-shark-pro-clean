# V818 Telegram Pro Automation QA

Telegram publico queda limitado a futbol profesional y competiciones importantes usando `engines/telegram_professional_scheduler.py` junto al filtro V814/V815/V816 ya existente.

Bloqueos cubiertos:

- NBA y otros deportes.
- Juveniles, reservas, regionales menores y amistosos flojos.
- Ligas sin valor comercial.
- Errores tecnicos en canal publico.
- Reenvios duplicados por fecha Madrid/job/destino/tipo.

El envio real sigue pasando por el scheduler existente, que conserva dedupe, quiet hours y limites.
