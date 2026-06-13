# RELEASE ZIP AUDIT V750

- Versión: `V750_CLIENT_LIVE_DAY_RELEVANCE_MADRID_RESULT_POLISH`
- ZIP: `NeMeSiS_SHARK_PRO_V750_CLIENT_LIVE_DAY_RELEVANCE_MADRID_RESULT_POLISH_RENDER_READY.zip`
- Archivos incluidos: 440
- ZIPs internos: 0
- Archivos prohibidos: 0
- Carpetas prohibidas incluidas: 0
- Render Ready: sí

## Limpieza confirmada

No incluye:

- `.git`
- `.venv`
- `__pycache__`
- logs
- bases de datos locales
- backups locales
- vídeos
- ZIPs internos
- secrets reales

## Validación destacada

- `/live`, `/directo` y `/en-directo` se mantienen como rutas cliente.
- La pantalla live se organiza por día, competición y relevancia.
- Se mantiene Madrid Time.
- No se inventan resultados: si no hay marcador real se muestra `vs`/estado adecuado.
- Telegram/Cron V749B no se modifica.
