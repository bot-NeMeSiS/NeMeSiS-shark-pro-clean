# V705 PICKS AND ODDS AUDIT

## Picks

V705 no baja calidad ni fabrica picks. Aumenta superficie de candidatos y automatizacion:

- Candidatos: hasta 80 en 21 dias.
- Admin Picks: hasta 220 partidos en 21 dias.
- Automation auto_picks: limite 80.
- Recommendations scheduler: limite 120.

Medicion controlada:

- Picks publicados: 12.
- Candidatos: 22.
- Recomendaciones: 22.

## Por que algunos partidos quedan fuera

- Partido finalizado o live cuando se busca prepartido.
- Sin local/visitante valido.
- Sin cuota o datos suficientes para elevar confianza.
- Membership/gating si el usuario no tiene plan adecuado.
- Filtros de calidad para no generar picks basura.

## Cuotas

V704/V705 aprovechan outcomes de The Odds API. V705 aumenta limites de sync:

- Odds scheduler: 250.
- Sync odds por defecto: 250.
- Mercados por env: `ODDS_MARKETS`, por defecto `h2h`.
- Regiones por env: `ODDS_REGIONS`, por defecto `eu,uk`.

Medicion controlada:

- Partidos con cuotas reconocidas: 28.

## Limitacion real

Para mas mercados no basta el codigo: hay que configurar `ODDS_MARKETS` y confirmar que The Odds API ofrece esos mercados para cada competicion.
