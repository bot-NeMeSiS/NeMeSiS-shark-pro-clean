@"
# V843 Real Data Commercial States QA

## Estados validados
- Próximo
- En directo
- Resultado
- Resultado pendiente
- Esperando proveedor
- Sin datos reales
- Sin picks activos
- Cuotas pendientes
- Conectar Telegram
- Madrid Time

## Correcciones aplicadas
- Picks usa Sin picks activos cuando no hay selección real suficiente.
- Calendario usa Sin datos reales y Esperando proveedor cuando el filtro no devuelve partidos reales.
- Se mantiene la regla de no inventar datos.

## Resultado
	ools/check_v843_real_data_commercial_states.py pasa correctamente.

## Validación final
El check V843 de estados comerciales pasa sin términos ausentes ni términos prohibidos visibles en templates principales.
