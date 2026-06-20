# V828 Client Shell Rebuild Report

## Objetivo

Acercar el cliente a las referencias: sidebar/rail desktop, topbar limpia, cards densas y bottom nav móvil única.

## Cambios

- Nuevo `v828-client-rail` en `templates/base.html`.
- Rail desktop con logo, navegación principal, plan y salida.
- Topbar cliente deja de repetir toda la navegación en escritorio.
- Contenido cliente se desplaza para convivir con el rail.
- Mobile oculta rail y mantiene bottom nav única.
- Floating SHARK queda único y no aparece dentro de páginas SHARK.

## Navegación definitiva

Desktop cliente:

- Dashboard
- Partidos
- Directo
- Picks
- SHARK
- Histórico
- Telegram
- Perfil
- Soporte
- Salir

Mobile cliente:

- Inicio
- Partidos
- Directo
- Picks
- SHARK

## Compatibilidad

No se modificaron rutas Flask ni lógica de login, membresías, Telegram, pagos, Cron o DB.
