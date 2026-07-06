# V898 404 PWA Cache QA

## 404

La página 404 muestra:

- título premium;
- ruta solicitada saneada;
- acciones seguras;
- botón de restablecimiento PWA.

No muestra query strings sensibles ni tokens.

## PWA/cache

El botón `Restablecer app/PWA` ejecuta JS local del navegador:

- desregistra service workers;
- borra Cache Storage;
- redirige a `/`.

No toca servidor, usuarios, DB ni sesiones de backend.

## Service worker

Cache actual:

`NEMESIS_CACHE_V898`

Regla:

- navegación con 404 => fallback a `/`;
- no se usa `caches.open`;
- no se guarda 404 en caché.

