# V897 Route Alias Duplicate Fix QA

## Problema

V896 registraba aliases con decoradores Flask antes de rutas reales posteriores. Eso podía pisar rutas como:

- `/calendario`
- `/partidos-hoy`
- `/recomendaciones`
- `/ayuda`
- `/soporte`
- `/perfil`
- `/mi-cuenta`
- `/admin/client-screens`

## Solución

Se creó:

`register_alias_if_missing(source, target)`

Regla:

Si `source` ya existe como ruta real, no se registra alias.

## Resultado esperado

- Rutas reales preservadas.
- Aliases legacy útiles siguen activos.
- `/dashboard` redirige a `/app`.
- `/admin-panel` redirige a `/admin/dashboard`.
- `/directos` redirige a `/live`.

## QA local

`tools/check_v897_truthful_sentinel_route_alias_reference_qa.py` valida que los aliases no pisan rutas reales y que las rutas legacy principales siguen funcionando.

