# V822 Visual Regression Safety QA

## Conservado

- Topbar cliente unica.
- Bottom nav movil unica.
- SHARK flotante unico.
- `/shark` sin SHARK duplicado.
- Admin sin bottom nav.
- Rails viejos neutralizados por CSS V819.
- Escudos V820 con tamano controlado.

## Alcance

V822 no introduce rediseño grande. Solo añade marcador y contencion CSS minima para estabilidad.

## Validacion ejecutada

- `tools/check_v822_visual_regression_safety.py` OK.
- Checks V819 visual/dedup OK.
- Checks V820 client/mobile OK.
