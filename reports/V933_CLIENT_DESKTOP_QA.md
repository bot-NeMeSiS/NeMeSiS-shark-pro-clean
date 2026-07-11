# V933 Client Desktop QA

## Rutas revisadas

`/app`, `/calendar`, `/live`, `/picks`, `/track-record`, `/shark`, `/telegram`, `/profile`, `/memberships` y `/support`.

## Cambios

- Dashboard cliente con saludo real, plan, hora Madrid, KPIs, ruta recomendada, agenda, SHARK, Telegram y accesos rapidos.
- Calendario con filtros, busqueda, agrupacion y estado de proveedor separado del contenido cliente.
- Live con board, tabs, marcadores/minutos solo reales y alternativa de proximos partidos.
- Picks con puerta de calidad: partido, mercado, seleccion y cuota obligatorios.
- Historico sin graficas decorativas ni porcentajes falsos cuando no hay muestra.
- SHARK muestra capacidades y limites del modo seguro.
- Telegram no afirma conexion ni envios sin evidencia.
- Perfil y planes separan estado, acciones, seguridad y membresia.

## Evidencia

Capturas autenticadas desktop: 40. Los cuatro anchos se renderizaron sin overflow horizontal, redireccion a login ni error de captura. La navegacion cliente permanece separada de admin.

## Datos

No se copiaron partidos, cuotas, ROI, usuarios ni ingresos de las referencias. Cuando faltan filas reales se muestra una accion util y un estado compacto.

