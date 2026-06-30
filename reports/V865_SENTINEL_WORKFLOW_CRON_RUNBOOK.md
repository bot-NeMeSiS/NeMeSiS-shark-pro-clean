# V865 Sentinel Workflow Cron Runbook

Endpoint:

`/api/automation/continuous-sentinel/run?mode=workflow&dry_run=1`

Comportamiento:

- Ejecuta diagnóstico estático.
- Agrupa incidencias.
- Crea tareas propuestas.
- Genera prompts Codex.
- Devuelve resumen de workflow.

Seguridad:

- Sin `AUTOMATION_SECRET` debe devolver 403.
- Con secreto válido puede devolver 200 en modo dry-run.
- No debe tocar código.
- No debe hacer deploy.
- No debe tocar secretos.
- No debe tocar pagos/usuarios/DB real.
- No debe enviar Telegram real.
- No debe llamar APIs externas caras.

Uso recomendado:

1. Ejecutar en dry-run.
2. Revisar panel admin.
3. Copiar prompt si procede.
4. Aplicar mejora con Codex/Admin.
5. Revalidar con Sentinel.
6. Marcar issue como resuelto solo tras validación.
