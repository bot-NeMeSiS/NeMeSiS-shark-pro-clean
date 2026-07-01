# V881 Nav Render Source Map

## Fuente única por zona

1. Cliente desktop nav: `templates/base.html` -> `nav.nav-clean[data-nav-zone="client-topbar"]`.
2. Cliente mobile bottom nav: `templates/base.html` -> `nav.bottom-nav-clean[data-nav-zone="client-bottom"]`.
3. Admin desktop nav: `templates/base.html` -> `aside.v808-admin-rail`.
4. Admin mobile/compact nav: mismo `v808-admin-rail`, sin bottom nav cliente.
5. Floating SHARK cliente: `templates/base.html` -> `div.shark-widget`, solo si `show_floating_shark`.
6. Admin command strip: retirado como fuente de navegación principal.
7. Quick actions dentro de cards: permanecen dentro de cada pantalla, no son navegación global.

## Regla V881

No debe haber dos fuentes globales renderizando los mismos destinos en la misma vista.
