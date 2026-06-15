# V797_RENDER_VISUAL_QA_LOGOUT_REAL_DATA_PIXEL_POLISH

Pasada basada en vídeo real de Render.

## Objetivo
- Acercar cliente/admin a los mockups aprobados.
- Añadir salida/cerrar sesión clara.
- Evitar datos ficticios en admin: cuando no hay datos reales, mostrar pendiente/—.
- Mantener enlaces y ecosistema sin romper Stripe, Telegram, Cron, DB_PATH, Madrid Time ni datos reales.

## Cambios principales
- Botón visible de “Cerrar sesión” para cliente: top/nav, flotante seguro y card destacada en Mi cuenta.
- Admin sidebar/topbar con salida clara.
- Admin dashboard, pagos, Telegram, automatización y data marketplace reducen datos mock/fake y muestran estados real-only.
- CSS V797 refuerza profundidad visual, cards, hero, empty states y notas de datos reales.
- Check V797 añadido.

## Guardrails
No se tocaron secretos, DB_PATH, Stripe core/webhook/portal, Telegram delivery real, Cron real, usuarios/sesiones/membresías, picks reales, directos, escudos, Track Record, legal ni Madrid Time.
