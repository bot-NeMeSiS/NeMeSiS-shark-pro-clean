# V875 Logos Crests Product QA

## Runtime real

- `team_logo_cache_count=0`.
- `league_logo_cache_count=0`.
- `logo_cache_ready=true`.
- `logo_routes_ok=true`.

## Estado seguro esperado

- Fallback visual activo.
- Iniciales/badge premium si no hay escudo.
- Estado `Escudo pendiente` si procede.
- No imagen rota.
- No descarga masiva.
- No inventar escudos oficiales.

## Siguiente accion

Despues del deploy V875, revisar cards de partidos/live/picks en produccion y poblar cache solo mediante job protegido o accion admin segura.

