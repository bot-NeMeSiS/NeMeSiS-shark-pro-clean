# V764 Dynamic Mode — QA cliente

## Pantallas revisadas por diseño
- `/`
- `/modo-dinamico`
- `/mundial`
- `/calendar`
- `/live`
- `/picks`
- `/menu`

## Validaciones funcionales esperadas
- El cliente ve un modo automático claro.
- El modo no muestra JSON ni lenguaje de admin.
- El modo explica por qué se activó.
- Si hay live, debe priorizar live.
- Si hay Mundial, debe priorizar Mundial.
- Si hay Champions/Europa/España, debe adaptar la agenda.
- Si hay picks, deben verse con partido/hora/contexto.
- Si no hay datos, debe mostrar mensaje honesto.
- Home, Calendar, Live, Picks y Mundial mantienen navegación clara.

## Validaciones técnicas
- `VERSION.txt` y `APP_VERSION` apuntan a V764.
- `/api/client/dynamic-mode` existe.
- `/modo-dinamico` existe.
- `templates/dynamic_mode.html` existe.
- `static/app.css` contiene CSS V764.
- Telegram/Cron/DB_PATH intactos.
