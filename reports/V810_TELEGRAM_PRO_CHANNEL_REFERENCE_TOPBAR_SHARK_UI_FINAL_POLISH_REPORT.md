# V810 Telegram PRO Channel + Reference Topbar/SHARK UI Final Polish

## Objetivo
Cerrar Telegram en modo profesional y seguir acercando cliente/admin al formato de las fotos.

## Cambios
- Telegram automático filtrado para primeras ligas y campeonatos importantes.
- Bloqueo de ligas raras, juveniles, reservas, amistosos, regionales y divisiones inferiores para el canal.
- Nuevos formatos premium de mensajes: resumen TOP, live TOP y pick SHARK PRO.
- Nueva pantalla admin `/admin/telegram/pro-preview` para ver previews sin enviar nada.
- Barra superior cliente/admin más parecida a las referencias.
- Tiburón decorativo grande añadido como fondo visual.
- Botón SHARK flotante deduplicado; si aparecen varios, se conserva uno solo.
- En móvil se conserva la navegación limpia: Inicio, Partidos, Directo, Picks, SHARK.
- Corregido enlace roto `/sharkteam=` a `/shark?team=`.

## Protecciones
No se tocan DB_PATH, secretos, usuarios, membresías, pagos, Telegram real, Cron ni claves API. No se inventan partidos, picks, cuotas, resultados, ataques ni eventos.
