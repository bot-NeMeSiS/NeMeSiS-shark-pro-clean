# V856 Rutas y Botones Segunda Pasada

## Cliente revisado
- `/app` debe orientar a partidos, live, picks, SHARK, Telegram, perfil y soporte.
- `/partidos`, `/calendar` y `/live` deben enlazar a detalle cuando exista partido real.
- `/picks` debe enlazar a partido y SHARK solo si existe contexto real.
- `/shark` debe enlazar a partidos, live, picks, Telegram y soporte.
- `/profile` debe enlazar a Telegram, soporte, histórico, favoritos y logout donde aplique.

## Admin revisado
- `/admin/dashboard` debe enlazar a datos, API-SPORTS, Telegram, SHARK, automatización, usuarios, membresías y pagos.
- `/admin/data-center` debe orientar a proveedores, runtime y health.
- `/admin/telegram/command-center` mantiene calidad V844.
- `/admin/shark-ai` mantiene estado V845.

## Corrección V856
- Se añadieron motores de presentación con CTAs claros para cliente, admin, match, live, picks, Telegram y SHARK.
- Se añade check V856 para detectar rutas clave ausentes y evitar botones muertos evidentes.

## Nota
Si una ruta no existe en una instalación concreta, el smoke debe documentarlo y usar alias real existente. V856 no inventa rutas nuevas sin conexión.
