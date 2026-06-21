# V843 Client Flow Final QA

## Flujo revisado
- Landing, login y registro: entrada clara al producto.
- /app: centro de navegación hacia partidos, directo, picks, SHARK, perfil, Telegram y soporte.
- /partidos y /calendar: calendario con filtros, detalle y estados reales.
- /live y /directo: acceso al centro de directo sin inventar minutos ni marcadores.
- /picks: selección real con enlace a partido y SHARK.
- /match/: detalle conectado con picks, partidos y SHARK.
- /shark: pantalla de consulta y apoyo al análisis.
- /profile: cuenta, plan, Telegram, favoritos, histórico y salida.
- /telegram: estado de conexión y soporte.
- /support: ayuda y retorno al ecosistema.
- /track-record, /favorites, /combis, /mercados y /highlights: se mantienen conectadas y sin datos inventados.

## Correcciones de flujo
- /sharkpick=... pasa a /shark?pick=....
- /sharkteam=... pasa a /shark?team=....
- /combistipo=... pasa a /combis?tipo=....
- /mercadostipo=... pasa a /mercados?tipo=....
- /calendarleague=... pasa a /calendar?league=....
- /liverefresh=1 pasa a /live?refresh=1.
- /match-hublane=... pasa a /match-hub?lane=....
- /membresiasplan=... pasa a /membresias?plan=....

## Resultado
No se detectan botones principales vacíos ni enlaces internos mal formados tras la corrección.
