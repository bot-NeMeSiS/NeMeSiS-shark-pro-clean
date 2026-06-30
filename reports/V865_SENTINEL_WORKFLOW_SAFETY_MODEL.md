# V865 Sentinel Workflow Safety Model

Acciones permitidas:

- Deduplicar incidencias.
- Recalcular prioridad.
- Marcar incidencias como reconocidas.
- Actualizar estado de issue.
- Regenerar reportes.
- Limpiar caché propia del Sentinel.
- Generar tareas.
- Cerrar issue solo tras revalidación local.

Acciones que requieren aprobación:

- Cambiar `app.py`, templates o CSS.
- Ejecutar deploy.
- Usar credenciales reales.
- Enviar Telegram test real.
- Sincronizar proveedor real.
- Modificar datos de membresía.
- Cerrar incidencias dependientes de Render real.

Acciones bloqueadas automáticamente:

- Modificar código automáticamente.
- Hacer deploy automático.
- Tocar secretos.
- Tocar pagos reales.
- Borrar usuarios.
- Borrar DB.
- Enviar Telegram masivo.
- Inventar picks, cuotas o resultados.
