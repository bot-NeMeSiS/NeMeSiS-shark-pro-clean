# V832 Visual Layers Final Cleanup

## Revisión

Se mantiene la limpieza V830 de bottom nav y floating SHARK, y se añade V832 como capa final de consistencia. No se eliminó código a ciegas.

## Neutralizado / protegido

- Bottom nav duplicada en desktop.
- Floating SHARK en admin.
- Floating SHARK dentro de pantallas SHARK.
- Flecha scroll-to-top en mobile por V830.
- Overflow horizontal con reglas globales heredadas V830.
- Admin con fondo sobrio y sin elementos cliente.

## Mojibake / literales

Se mantiene el título base seguro: `{% if title is defined and title %}`. No debe aparecer el literal roto `{{ title or 'NeMeSiS SHARK PRO' }}` en navegador.
