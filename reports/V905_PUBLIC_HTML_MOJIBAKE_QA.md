# V905 Public HTML Mojibake QA

## Revisado

- `templates/base.html`.
- `templates/home.html`.
- HTML público de `/`.
- Cache PWA/service worker.

## Correcciones

- Se corrigió `experiencia nica` a `experiencia única`.
- Se corrigieron labels visibles de `Membresias` a `Membresías` en base/nav donde aplicaba.
- Se actualizó cache PWA a `NEMESIS_CACHE_V905` para evitar HTML antiguo.

## Estado

- No se detectó BOM al inicio de `base.html`.
- El check V905 valida que `/` no empiece con restos `rn` ni BOM visible.
- No se declara pixel-perfect sin Browser QA real.
