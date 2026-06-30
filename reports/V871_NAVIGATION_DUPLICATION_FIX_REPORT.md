# V871 Navigation Duplication Fix Report

## Cliente
- Rail lateral ahora usa label + descriptor, no label duplicado.
- Ejemplos: `Picks / Premium`, `SHARK / IA`, `Telegram / Canal`.
- Bottom nav conserva cinco accesos principales.

## Admin
- Rail admin evita pares repetidos.
- Admin mantiene ocultos bottom nav, floating SHARK cliente y accesos móviles cliente por CSS.
- Command strips y docks no se eliminan para no romper flujo V853/V870.

## JavaScript base
Se repararon ternarias dañadas que podían impedir:
- lectura de CSRF;
- favoritos;
- navegación activa;
- detección móvil/tablet/desktop;
- reloj admin.
