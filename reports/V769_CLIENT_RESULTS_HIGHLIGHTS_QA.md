# V769 Client Results / Highlights QA

Pantallas a revisar tras deploy:

- `/resumenes`: centro principal de resultados y vídeos.
- `/resumen/<id>`: detalle individual de resumen.
- `/calendar?lane=results`: resultados con estado de resumen.
- `/live?f=finished`: finalizados y enlace a resumen si existe.
- `/match/<id>`: marcador, estado y resumen embebido/externo.
- `/track-record`: evidencia visual de resultados.
- `/`: bloque de últimos resúmenes sin saturar home.
- `/admin/highlights-center`: panel admin de control.

Checklist:

- No aparecen textos técnicos de admin en cliente.
- Si no hay vídeos, se muestra estado vacío claro.
- Si falta key de TheSportsDB, se informa sin romper pantalla.
- Si hay vídeo YouTube, se usa `youtube-nocookie`.
- Si no se puede embeber, se muestra botón de fuente externa.
- No se descargan ni rehostean vídeos.
- Todo horario visible sigue Madrid/España.
- Telegram/Cron Telegram siguen intactos.
