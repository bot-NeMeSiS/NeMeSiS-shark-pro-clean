# V871 Auditoría de Botones, CTAs y Copy Duplicado

## Hallazgos reales
- La navegación cliente/admin tenía etiquetas repetidas en la V871 intermedia ya corregida.
- Telegram tenía copy roto en palabras de conexión y vinculación.
- Las macros podían generar botones con label poco accesible si faltaba texto.
- El Sentinel marcaba como botón algunas filas deportivas completas, generando falsos positivos.

## Correcciones
- Botones de navegación con etiqueta principal y secundaria diferenciadas.
- Macros `action_button` y `reference_action_button` mantienen un solo texto visible y `aria-label` separado.
- Sentinel revisa CTAs y evita tratar filas de partido como botones simples.

## Estado
No quedan duplicados evidentes tipo `Panel Panel`, `SHARK SHARK`, `Telegram Telegram` o `Partidos Partidos` en la shell principal.
