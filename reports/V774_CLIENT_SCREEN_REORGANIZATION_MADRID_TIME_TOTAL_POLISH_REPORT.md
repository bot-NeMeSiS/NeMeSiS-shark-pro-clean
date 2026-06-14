# V774_CLIENT_SCREEN_REORGANIZATION_MADRID_TIME_TOTAL_POLISH

## Objetivo

Esta versión corrige el punto crítico detectado en los vídeos: la zona cliente seguía demasiado caótica, con muchas capas acumuladas de versiones anteriores, navegación saturada, pantallas repetidas y fechas/horas que no se entendían bien de un vistazo.

## Cambios principales cliente

- Home cliente reconstruida con una sola experiencia: partidos, directo, picks, SHARK e histórico.
- Landing pública aislada: ya no se mezcla debajo del panel cliente al estar logueado.
- Navegación cliente reducida: Inicio, Partidos, Directo, Picks, Histórico, SHARK y Más.
- Menú Más reorganizado para Mercados, Combis, Resúmenes, Mundial, Telegram, Cuenta, Ayuda y Legal.
- Calendario reconstruido con tabs, búsqueda, date rail, ligas y tarjetas claras.
- Corrección de chip confuso de calendario: `Pasado` para +2 días pasa a `En 2 días`.
- Calendario enriquecido con contexto cliente Madrid mediante `client_match_display_context`.
- Directo reconstruido: directos, próximos y finalizados separados por día/estado.
- Picks reconstruidos: qué apostar, mercado, cuota, stake, riesgo y lectura SHARK visibles.
- Combis reconstruidas: estrategias, estado lista/en estudio, cuota total y patas visibles.
- Mercados reconstruidos: menos ruido y más explicación para 1X2, DNB, goles y BTTS.
- Resúmenes reconstruidos: disponibles y pendientes separados.
- Track Record reconstruido: ROI/winrate solo con datos reales, pendientes separados.
- Detalle de partido reconstruido: marcador, hora Madrid, estado, lectura SHARK, picks relacionados y timeline.
- Sports Hub reconstruido para que sea coherente con calendario/directo.

## Cambios de estabilidad visual

- Nueva capa CSS V774 para tarjetas, listas, hero, filtros, tabs, calendar cards y mobile-safe bottom nav.
- El widget SHARK queda más separado del bottom nav para no tapar contenido.
- Se ocultan de la navegación principal cliente rutas secundarias como Momento, Mercados y Resúmenes; siguen disponibles en Más.
- Se ocultan bandas repetitivas antiguas en pantallas cliente autenticadas para reducir ruido visual.

## No se ha tocado

- DB_PATH.
- Usuarios.
- Sesiones.
- Membresías.
- Pagos foundation.
- Telegram manual.
- Telegram automático.
- `/api/automation/telegram/tick`.
- `tools/render_cron_telegram_tick.py`.
- `AUTOMATION_SECRET`.
- Track Record/grading.
- Highlights engine.
- Data Marketplace.
- Automation Center.
- Madrid Time engine.

## Validaciones

- `py_compile app.py` OK.
- `compileall app.py engines tools` OK.
- `tools/check_v774_client_screen_reorganization_madrid_time.py` OK.
- `tools/check_madrid_times.py` OK.
- `tools/check_v771_telegram_activity_pro_format_schedule.py` OK con Flask skip en sandbox.
- `tools/check_v772_telegram_visual_cards_app_global_polish.py` OK con Flask skip en sandbox.
- `tools/check_v773_data_marketplace_automation_video_ux_quality.py` OK con Flask skip en sandbox.
- Jinja parse: 136 plantillas, 0 errores.

## Pendiente producción

- Validar visualmente en Render las pantallas cliente: `/`, `/app`, `/calendar`, `/live`, `/picks`, `/combis`, `/mercados`, `/highlights`, `/track-record`, `/match/<id>`, `/menu`.
- Confirmar con datos reales que todos los partidos muestran día + hora Madrid correcta.
- Confirmar Telegram real con Render env y canal reales.
