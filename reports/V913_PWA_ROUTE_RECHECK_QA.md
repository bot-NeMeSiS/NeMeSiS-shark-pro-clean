# V913 PWA Route Recheck QA

## Resultado esperado

- Service worker cache: `NEMESIS_CACHE_V913`.
- No cachear 404.
- `/ruta-inventada` devuelve 404 premium.
- `/api/ruta-inventada` devuelve JSON 404 seguro.
- Manifest sigue disponible.

## Estado

V913 mantiene la politica PWA/404 de V906B-V912 y actualiza cache a V913.
