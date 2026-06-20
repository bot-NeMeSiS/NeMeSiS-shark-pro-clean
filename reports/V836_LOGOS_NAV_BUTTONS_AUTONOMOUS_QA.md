# V836 Logos Nav Buttons Autonomous QA

## Logos

- Logo SHARK principal usa `static/img/shark-logo.svg`.
- Se refuerza `object-fit: contain` para evitar deformaciones.
- Se mantiene fallback de escudos sin descargar logos en runtime.

## Barras

- Topbar cliente única.
- Rail cliente desktop único.
- Bottom nav móvil única.
- Topbar/rail admin separados.
- Admin sin floating SHARK cliente.
- Admin sin bottom nav cliente.

## Botones

- Botones principales mantienen altura mínima cómoda.
- CTA principales usan gradiente premium.
- Botones de navegación conservan href real.
- Botón de scroll arriba se oculta en móvil para evitar solapamientos.

## Corrección principal V836

Se refuerzan las reglas que evitan duplicados visuales y elementos flotantes mal ubicados, sin tocar rutas ni lógica.
