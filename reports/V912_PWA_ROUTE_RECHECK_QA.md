# V912 PWA / 404 Route Recheck QA

## Objetivo

Preservar PWA/404 recovery y actualizar cache de service worker a V912.

## Resultado

- Service worker usa `NEMESIS_CACHE_V912`.
- `/manifest.json` responde 200 local.
- `/service-worker.js` responde 200 local.
- Ruta HTML inventada responde 404 premium.
- Ruta API inventada responde JSON 404 seguro.
- Se mantiene guard para no cachear 404.

## Estado

OK local. Requiere deploy manual para que producción sirva V912.
