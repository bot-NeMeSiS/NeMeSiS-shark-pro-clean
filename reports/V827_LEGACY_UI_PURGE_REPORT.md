# V827 Legacy UI Purge Report

## Neutralizado

- Acciones secundarias antiguas de cliente (`v811-top-actions`, `v797-session-pills`) se ocultan en V827 para no duplicar navegación.
- Floating SHARK se mantiene único y se oculta en /shark, /shark-ai y /shark-core.
- Admin queda sin fondo/floating de cliente.
- Estilos viejos de cards, rows y botones quedan normalizados por el bloque V827.

## No eliminado físicamente

No se borraron templates ni bloques históricos porque siguen aportando compatibilidad y datos. Se neutralizó visualmente lo que duplicaba navegación o identidad.

## Riesgo evitado

No se tocaron rutas críticas, lógica de Telegram, cron, DB_PATH, Madrid Time, pagos ni membresías.
