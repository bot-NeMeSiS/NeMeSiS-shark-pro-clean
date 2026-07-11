# V930 Client Mobile Visual QA

## Resultado

- Header móvil compacto y logo visible.
- Bottom nav fija con cinco destinos: Inicio, Partidos, Directo, Picks y Cuenta.
- Contenido comienza a 70 px, por debajo del header de 58 px.
- Reserva inferior con safe area; ningún bloque queda oculto bajo la navegación.
- KPIs 2x2, cards verticales, botones táctiles y filtros horizontales controlados.
- Desktop nav oculta en móvil.
- Capturas reales en 390x844 y 430x932; CSS cubre también 360/375/412 mediante breakpoints fluidos.
- Overflow de documento: 0.

Rutas revisadas: app, calendario, live, picks, histórico, SHARK, Telegram, perfil, planes y detalle contextual. No se declara pixel-perfect sin revisión humana.
