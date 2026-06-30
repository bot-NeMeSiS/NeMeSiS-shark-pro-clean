# V862 Sentinel Safe Autofix Policy

## SAFE_SUGGESTION

- Recomendar texto.
- Recomendar ruta.
- Recomendar CSS.
- Recomendar prompt Codex.

## SAFE_RUNTIME_ACTION

- Refrescar diagnóstico.
- Limpiar caché propia si existe y es seguro.
- Marcar issue como revisado.
- Generar reporte.

## REQUIRES_ADMIN_APPROVAL

- Crear prompt Codex como tarea.
- Ejecutar sync.
- Enviar Telegram test.
- Tocar membresías.
- Archivar picks.
- Preparar release.

## FORBIDDEN_AUTOMATIC

- Modificar `app.py`.
- Cambiar templates automáticamente en producción.
- Deploy.
- Tocar secretos.
- Borrar DB.
- Borrar usuarios.
- Pagos reales.
- Telegram masivo.
- Inventar picks, cuotas o resultados.
