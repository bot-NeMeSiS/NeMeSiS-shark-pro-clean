# V868 Auditoría visual real cliente/admin

Hallazgos principales:

- Cliente PC ya tiene fondo SHARK, cards y rutas, pero necesitaba una capa más compacta para que `/app`, `/picks` y `/live` se lean como dashboard premium y no como bloques grandes independientes.
- Móvil ya tenía protección V866 contra overflow, pero faltaba reforzar grids, filtros horizontales y acciones para evitar scroll lateral en cards de picks/live/Sentinel.
- Admin mantiene Company OS, Product Board y Sentinel, pero las pantallas de flujo necesitaban más densidad visual y ocultar cualquier navegación flotante cliente en contexto admin.
- Sentinel Workflow tenía copy útil, pero se revisó especialmente para evitar mojibake visible y dejar más claro que no modifica código ni despliega sin aprobación.
- Picks/live mantienen estados seguros, pero V868 refuerza visualmente chips y tarjetas para separar cuota pendiente, selección pendiente y pick en revisión.

Corrección aplicada:

- Capa CSS V868 transversal para cliente/admin/móvil.
- Versionado V868 y cache busting.
- Flag runtime `has_v868_real_client_admin_visual_polish`.
- Corrección de textos visibles Sentinel/UI ya verificada por checks.
