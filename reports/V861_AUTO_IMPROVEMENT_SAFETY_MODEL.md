# V861 Auto-Improvement Safety Model

## Principios

- Diagnóstico primero.
- Acción segura solo si no afecta datos, secretos, código ni proveedores.
- Aprobación admin para acciones sensibles.
- Prohibición total de acciones destructivas automáticas.

## Bloqueos permanentes

V861 nunca debe hacer automáticamente:

- Modificar `app.py` o código de producto.
- Hacer deploy a Render.
- Leer, mostrar o modificar secretos.
- Borrar DB, usuarios, sesiones, membresías o pagos.
- Enviar Telegram masivo.
- Inventar picks, cuotas, resultados, minutos, estadísticas o ROI.
- Ejecutar llamadas API caras sin guard y aprobación.

## Datos reales

Si falta dato real, se usan estados seguros como `Esperando proveedor`, `Cuotas pendientes`, `Resultado pendiente`, `Sin directos reales` o `No configurado`.
