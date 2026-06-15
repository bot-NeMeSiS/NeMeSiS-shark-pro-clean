# V800_REFERENCE_SCREEN_APP_FIDELITY_REAL_DATA_NAVIGATION_FINAL

## Objetivo
Avance visual sobre V799 para acercar la experiencia cliente a las pantallas de referencia: app oscura premium, lectura rápida, navegación clara, partido/pick/SHARK conectados y sin datos inventados.

## Cambios principales
- Añadida capa global `data-v800-shell` para cliente autenticado.
- Mejorado rail lateral cliente con estado “Datos reales · Hora Madrid”.
- Activación visual de navegación actual en rail, top nav y bottom nav.
- Añadido bloque visual V800 en Home y App Center con partido foco, pick real y acceso SHARK.
- Añadida fila de comandos V800 en Calendario y Picks.
- Añadido ticker visual V800 en Directo.
- Añadida lectura rápida de pick: qué apostar, por qué entrar y cuidado/riesgo.
- Añadida tira de acciones en detalle de partido: resumen, pick, datos y SHARK.
- Añadida tira segura de cuenta: Telegram, plan, favoritos y cerrar sesión.
- Añadido flujo Telegram: vincular bot, revisar plan y recibir alertas reales.

## Reglas conservadas
- No se inventan partidos, cuotas, resultados, ROI, confianza ni picks.
- Si falta dato, se muestra estado vacío: pendiente, sin pick, esperando sincronización o sin dato real.
- No se tocan secretos, DB_PATH, usuarios, membresías, pagos, Cron ni motor Telegram automático.
- Madrid Time se mantiene como fuente visual para horarios.

## Validación esperada
- `python -m py_compile app.py`
- `python -m compileall app.py engines tools`
- `python tools/check_madrid_times.py`
- `python tools/check_v798_reference_visual_client_flow_real_data.py`
- `python tools/check_v799_reference_screen_visual_polish.py`
- `python tools/check_v800_reference_screen_app_fidelity.py`
- Parse Jinja de plantillas
- Build ZIP limpio Render Ready
