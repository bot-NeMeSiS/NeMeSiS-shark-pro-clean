# V764_DYNAMIC_COMPETITION_MODE_ENGINE

## Objetivo
Activar un modo automático de experiencia cliente para que NeMeSiS SHARK PRO cambie el foco según el momento real del fútbol: Mundial, directo, Champions/Europa, España, fin de semana, picks activos, resultados o agenda normal.

## Implementado
- Nuevo motor contextual en `app.py`: `build_v764_dynamic_competition_mode()`.
- Detección automática por competición, estado, hora Madrid, picks y disponibilidad de datos reales.
- Nuevas rutas cliente:
  - `/modo-dinamico`
  - `/modo-competicion`
  - `/competition-mode`
- Nueva API cliente:
  - `/api/client/dynamic-mode`
- Nueva plantilla:
  - `templates/dynamic_mode.html`
- Bloque “Modo automático” inyectado en Home, Calendar, Live, Picks y Mundial.
- Navegación cliente añade “Momento” y menú cliente añade “Modo automático”.
- CSS V764 para la banda de modo automático, foco y KPIs.

## Modos automáticos
- Modo Directo: si hay partidos en directo.
- Modo Mundial: si hay Mundial/selecciones.
- Modo Champions: si hay Champions/UCL.
- Modo Europa: si hay competición UEFA/europea.
- Modo España: si hay competiciones españolas/Andalucía.
- Modo Picks del día: si hay picks activos.
- Modo Resultados: si predominan finalizados.
- Modo Fin de semana: agenda de viernes-sábado-domingo.
- Modo Ligas top: Premier, Bundesliga, Serie A, Ligue 1, Portugal, etc.
- Modo Próximos focos: si no hay datos suficientes.

## Reglas conservadas
- No se toca Telegram automático.
- No se toca Cron Render.
- No se toca `tools/render_cron_telegram_tick.py`.
- No se toca `/api/automation/telegram/tick`.
- No se cambia `AUTOMATION_SECRET`.
- No se cambia `DB_PATH`.
- No se inventan picks, cuotas, resultados ni ROI.
- Todo lo visible para cliente usa hora Madrid cuando hay dato disponible.

## Limitaciones honestas
- El modo automático depende de los datos reales sincronizados en Render y de la base persistente.
- Si no hay partidos/picks reales, muestra estado vacío premium sin inventar contenido.
- No se realizó envío real de Telegram desde sandbox.
