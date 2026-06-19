# V817 Screenshot Reference QA

## Estado

No se generaron screenshots reales con navegador en esta sesion.

## Validacion sustituta

Se valida por:

- parse de templates Jinja;
- Flask test client en rutas clave;
- HTML renderizado con `data-v817-shell`;
- comentario fuente V817;
- CSS V817 con cache-busting;
- checks `tools/check_v817_*`.

## Resultado ejecutado

- Jinja: 148 templates parseados sin errores.
- Smoke cliente/admin: OK, 0 rutas con 500.
- Runtime V817: OK.
- ZIP audit final: OK, `forbidden_count = 0`.

## Nota honesta

No se declara pixel-perfect. V817 es una aproximacion visual fuerte a las referencias usando las pantallas reales disponibles.
