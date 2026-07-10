# V929 Dynamic Routes QA

- `resolve_safe_internal_route()` valida endpoint, parametros y rutas internas sin lanzar BuildError.
- Partido, equipo y highlight inexistentes devuelven 404 contextual, no 500 ni redireccion generica.
- La pantalla contextual ofrece Inicio, Partidos, Calendario y Picks.
- El detalle de partido solo sincroniza proveedor externo con `refresh=1` explicito.
- No se inventan IDs, equipos, cuotas, resultados ni picks.
