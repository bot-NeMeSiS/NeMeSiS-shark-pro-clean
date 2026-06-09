# V704 COVERAGE AUDIT

## Auditoria de cobertura real

### Sports Hub

Antes habia recortes visibles en picks, semana, favoritos, live y top leagues. Ahora Sports Hub puede mostrar muchos mas partidos por filtro sin cambiar la estructura visual.

Capacidad tras V704:

- Hoy: hasta 200 partidos.
- Live: hasta 80 partidos.
- Proximos: hasta 160 partidos.
- Semana: hasta 220 partidos.
- Finalizados: hasta 120 partidos.
- Con cuotas: hasta 80 partidos.
- Con picks: hasta 80 partidos.

### Today

`/today` usa Sports Hub. En smoke local mostro 10 partidos de hoy sobre 16 totales.

### Live

En smoke local se validaron 2 partidos live. La cobertura live real depende de que la fuente marque estados live/minuto correctamente.

### Calendar

Calendar queda beneficiado por `get_matches()` y `get_upcoming_matches()` ampliados. Ya no queda limitado a 150 por defecto.

### Picks

Picks y candidatos se ampliaron. En smoke local:

- Picks publicados: 6.
- Candidatos: 12.
- Recomendaciones: 12.

### Recommendations

`v565_recommendation_pool()` ya podia leer hasta 250 partidos proximos; V704 aumenta quienes llegan desde la experiencia de cliente.

### Match Detail

No se cambia la logica visual de V703, pero se beneficia de mas partidos accesibles y mas cuotas reconocidas.

### SHARK

SHARK tiene mas superficie porque entran mas candidatos. Sigue sin inventar pick real si falta cuota o datos suficientes.

## Que limita actualmente la cobertura

1. Cantidad real de partidos guardados en SQLite.
2. Claves y permisos de APIs externas.
3. Disponibilidad de competiciones en The Odds API.
4. Configuracion de `ODDS_REGIONS` y `ODDS_MARKETS`.
5. Cache activa de Odds: evita llamadas repetidas, pero puede retrasar nueva cobertura si no se fuerza sync.
6. Identidad visual de equipos si no hay logos cacheados.
7. Calidad: el sistema evita publicar picks sin base suficiente.

## Cifras honestas

- En workspace local no hay DB real de produccion.
- La medicion de smoke sirve para validar capacidad y renderizado, no para afirmar volumen real de Render.
- Para cifras reales hay que ejecutar `/api/matches/diagnostics`, `/api/odds/diagnostics` y Data Center en Render.
