# V775 Mobile Client App Experience Total Completion

## Objetivo
Corregir el caos móvil detectado en el vídeo y cerrar una experiencia cliente coherente en móvil, PC y pantallas principales.

## Cambios principales
- Barra inferior móvil reducida a 5 accesos: Inicio, Partidos, Directo, Picks y Más.
- SHARK queda como botón flotante y página dedicada para no saturar la barra inferior.
- Home `/app` rehecha con entrada móvil clara, KPIs compactos, guía y focos.
- Menú Más reorganizado por grupos: seguir partidos, apostar con orden, cuenta/ayuda.
- Telegram cliente rehecho con layout V774/V775 y pasos claros.
- SHARK cliente rehecho y enlaces rotos corregidos (`/shark?q=...`, `/combis?...`).
- Cards de partido en móvil ahora muestran los dos equipos; no se oculta el visitante.
- Hero, botones, filtros, pestañas, rails, cards, picks y listas optimizados para pantallas pequeñas.
- Bottom nav y SHARK panel se ocultan cuando se abre teclado para evitar superposición.
- Se mantienen Madrid Time, Telegram, Cron, DB_PATH, usuarios, pagos, highlights, Track Record y Automation/Data Marketplace.

## Validación pendiente en Render
- Grabar vídeo móvil real tras desplegar.
- Confirmar que no hay scroll horizontal.
- Confirmar que el teclado no tapa SHARK ni filtros.
- Confirmar que Partidos, Directo, Picks, Más y Telegram se ven limpios en móvil real.
