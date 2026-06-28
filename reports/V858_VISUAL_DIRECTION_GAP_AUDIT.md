# V858 Visual Direction Gap Audit

## Problemas que V858 ataca
- Capas visuales acumuladas con jerarquía irregular.
- Cards con tamaños y densidades diferentes entre cliente, admin y Company OS.
- Estados vacíos que podían parecer error técnico.
- Navegación cliente/admin con riesgos de mezcla visual.
- Membresías con valor visual todavía dependiente de textos más que de sistema.
- SHARK y Telegram necesitaban una misma dirección premium.
- Tablas admin y filtros necesitaban densidad más profesional.

## Riesgos detectados
- Sin screenshots reales no se puede afirmar pixel-perfect.
- Sin Render real no se puede afirmar deploy real.
- Sin claves reales no se puede validar API-SPORTS/The Odds API/Telegram productivo.

## Corrección aplicada
- Sistema V858 de tokens visuales comunes.
- Fondo global oscuro premium con puntos, glow y profundidad.
- Cards, botones, chips, tablas, forms y empty states normalizados.
- Reglas explícitas para ocultar bottom nav/floating cliente dentro del admin.
- Company OS alineado con la dirección visual.
