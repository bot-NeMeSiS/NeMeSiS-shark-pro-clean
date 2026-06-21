# V844 App Wide Match Quality Hierarchy QA

## Alcance
La app puede seguir mostrando calendario amplio, pero Telegram y módulos destacados deben priorizar calidad comercial.

## Aplicación directa
- build_daily_matches_message filtra candidatos con V844.
- build_daily_picks_message filtra picks con V844.
- enqueue_live_alerts exige fútbol top.
- actividad V771 filtra partidos y picks antes de planificar mensajes.

## Resultado
Los partidos top tienen puntuación superior a competiciones regionales o débiles.
