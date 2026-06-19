# V824 Client Final Visual Experience Report

## Pantallas cliente tocadas

- `/app`
- `/calendar` / `/partidos`
- `/live` / `/directo`
- `/picks`
- `/match/<id>`
- `/shark`
- `/profile`
- `/telegram`
- `/support`

## Mejoras aplicadas

- Version y shell V824 activos.
- Capa visual final acotada a `body[data-v824-shell="true"]`.
- Topbar cliente mas legible y logo con mas presencia.
- Heroes y panels con textura deportiva, mayor contraste y menos planitud.
- Cards de partidos/directo/picks mas densas y compactas.
- Escudos/fallback con tamanos consistentes y mejor tratamiento visual.
- Bottom nav movil mas parecida a app.
- SHARK flotante sigue unico y se oculta en `/shark`.

## Sin cambios funcionales

- No se inventan partidos, cuotas, picks, resultados, minutos ni eventos.
- No se altera DB_PATH.
- No se toca Telegram/Cron/pagos/membresias.
