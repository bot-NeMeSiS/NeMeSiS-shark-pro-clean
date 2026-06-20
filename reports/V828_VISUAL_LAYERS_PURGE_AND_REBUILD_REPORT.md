# V828 Visual Layers Purge And Rebuild Report

## Capas detectadas

La app conserva capas visuales V724-V827. V828 no elimina código histórico de forma agresiva porque varias plantillas todavía dependen de clases heredadas.

## Neutralización segura

Se neutralizó desde CSS V828:

- Rails cliente antiguos: `.v798-client-rail`, `.v799-client-rail`, `.v800-client-rail`.
- Acciones flotantes antiguas de sesión: `.v797-session-pills`.
- Acciones duplicadas de topbar: `.v811-top-actions`.
- Day rail antiguo si provoca ruido: `.v801-day-rail`.
- Floating SHARK en `/shark`, `/shark-ai`, `/shark-core`.
- Bottom nav en escritorio cliente.

## Rebuild

Se añade una capa final ordenada:

- Tokens V828.
- Shell cliente.
- Rail desktop.
- Topbar secundaria.
- Cards compactas.
- Rows deportivas.
- Live center.
- Picks premium.
- SHARK hero.
- Admin command center.
- Mobile layout.

## No eliminado por seguridad

No se borraron templates, engines ni clases antiguas que puedan ser usadas por rutas históricas o por compatibilidad V818-V827.
