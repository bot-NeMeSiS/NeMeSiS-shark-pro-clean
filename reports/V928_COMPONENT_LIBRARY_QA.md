# V928 Component Library QA

## Biblioteca

V928 consolida la interfaz en:

- `templates/components/v928_ui.html`
- `templates/components/v928_navigation.html`
- `static/v928-canonical.css`

Se contabilizaron 33 macros reutilizables, incluyendo shells por rol, navegacion, encabezados, KPIs, estados, tablas, filtros, partidos, live, picks, cuotas, confianza SHARK, planes, perfil, proveedores, acciones y fallbacks de escudo.

## Consistencia

- Un shell publico, uno cliente y uno admin.
- Navegacion cliente desktop y bottom navigation movil diferenciadas.
- Sidebar y topbar admin aisladas del cliente.
- Cards, radios, espacios, chips, botones y tablas comparten tokens V928.
- Las reglas heredadas conflictivas quedaron neutralizadas dentro del shell V928.

## Verificacion

`tools/check_v928_component_consistency.py` finalizo correctamente. Jinja analizo los 171 templates sin errores.
