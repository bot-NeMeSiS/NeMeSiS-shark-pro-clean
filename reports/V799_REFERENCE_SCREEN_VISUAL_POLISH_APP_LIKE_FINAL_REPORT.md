# V799_REFERENCE_SCREEN_VISUAL_POLISH_APP_LIKE_FINAL

## Objetivo
Acercar las pantallas cliente a las referencias visuales aportadas: app deportiva premium oscura, sidebar tipo producto real, tarjetas compactas, preview móvil, navegación clara y estados vacíos elegantes sin inventar datos.

## Pantallas trabajadas
- `/app`, `/mi-app`, `/inicio`, `/panel-cliente`: nuevo centro visual V799 con hero, KPIs, ruta de uso, partidos destacados, pick destacado y preview móvil.
- `/`: home autenticada reforzada con la misma lógica visual cliente.
- `/calendar`: agenda real con filtros sticky, filas deportivas, CTA a detalle y SHARK.
- `/live`: marcador premium, feature live, cards compactas, estado vacío real si no hay directo.
- `/picks`: pantalla de picks reconstruida para explicar selección, cuota, stake, riesgo, confianza, motivos y riesgos sin inventar.
- `/match/<id>`: detalle con hero deportivo, meta real, datos disponibles, pick conectado y panel SHARK.
- `/mi-cuenta`: perfil/plan/Telegram/favoritos/pagos/salida con visual app.
- `/telegram`: conexión cliente con KPIs, beneficios y código visual.

## Cambios base
- `base.html` añade `data-v799-shell="true"`.
- Sidebar cliente ampliada en escritorio con marca, plan, navegación y botón `Salir`.
- Bottom nav móvil ajustada a: Inicio, Partidos, Directo, Picks, SHARK.
- Botones de cuenta/cerrar sesión siguen visibles mediante píldoras de sesión.
- `static/app.css` añade capa V799 completa responsive.

## Datos reales
- No se añaden partidos, cuotas, ROI, resultados, porcentajes o picks falsos.
- Los campos sin dato muestran `—`, `Pendiente`, `Sin pick`, `Sin dato real` o estados vacíos claros.
- Los picks ya no usan riesgo/stake/confianza inventados cuando el dato no existe.

## Preservado
- DB_PATH.
- Telegram/Cron y `/api/automation/telegram/tick`.
- AUTOMATION_SECRET.
- Madrid Time.
- Usuarios, sesiones, membresías y pagos.
- Rutas existentes.

## Validaciones locales
- `python -m py_compile app.py tools/build_clean_release.py` OK.
- `python -m compileall -q app.py engines tools` OK.
- Parse Jinja de 140 plantillas OK.
- `python tools/check_madrid_times.py` OK.
- `python tools/check_v798_reference_visual_client_flow_real_data.py` OK compatible V799.
- `python tools/check_v799_reference_screen_visual_polish.py` OK.

## Limitaciones
- En este sandbox no está instalado Flask, por lo que no se pudo ejecutar smoke test con test client.
- No se enviaron mensajes reales de Telegram.
- La validación final visual debe hacerse en Render con datos reales sincronizados y las capturas de referencia abiertas al lado.
