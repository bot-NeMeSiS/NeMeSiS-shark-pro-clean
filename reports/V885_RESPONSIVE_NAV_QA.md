# V885 Responsive Navigation QA

## Desktop

- `ns-client-sidebar` visible desde 1024px.
- Contenido principal se desplaza a la derecha del sidebar.
- Bottom nav cliente se oculta en desktop.
- Topbar cliente autenticado no duplica enlaces principales.
- Sidebar usa fondo premium, borde cian y estado activo.

## Mobile

- Sidebar cliente se oculta bajo 1024px.
- Bottom nav se muestra con 5 accesos.
- Main shell mantiene padding inferior para no quedar tapado.
- SHARK flotante sigue fuera de admin.

## Admin

- `ns-client-sidebar` oculto siempre.
- `bottom-nav-clean[data-nav-zone="client-bottom"]` oculto siempre.
- `shark-widget` oculto siempre en admin.

## Pendiente honesto

No se hicieron capturas reales en navegador, por lo que no se declara pixel-perfect.
