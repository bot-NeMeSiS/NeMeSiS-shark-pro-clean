# V930 Admin Visual QA

## Rutas modificadas

Dashboard, Telegram Command Center, usuarios, membresías, pagos, picks, partidos/sync, data center, automatización, daily automation, Workforce, Sentinel, incidencias, Outbox, navegación, lanzamiento, certificación y sistema.

## Resultado

- Sidebar fija y topbar separadas del cliente; búsqueda, incidencias e identidad admin visibles.
- KPIs y tablas densas; sin gráficas decorativas cuando no existen series reales.
- Estados de Telegram, pagos, APIs, DB, runtime, Sentinel y deploy se obtienen del contexto real o muestran pendiente.
- Workforce, Sentinel y Outbox ya no cortan títulos; Outbox no muestra rutas absolutas del PC.
- Admin móvil tiene header y carrusel de navegación propios; etiquetas completas y contenido a 124 px bajo el chrome.
- No hay navegación cliente ni SHARK flotante cliente en admin.
- Cero overflow y cero errores en las capturas.

Las acciones peligrosas siguen protegidas; la UI no envía Telegram, no cobra ni despliega por sí sola.
