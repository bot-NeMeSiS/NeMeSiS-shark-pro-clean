# V938 Second Operator Emergency Runbook

## Objetivo

Permitir que un segundo operador autorizado contenga una incidencia sin conocer secretos ni depender de memoria informal.

## Primeros diez minutos

1. Abrir Operations Center y `/api/runtime-version`.
2. Clasificar la evidencia: confirmado, no certificado o bloqueado por acceso.
3. Si hay riesgo de datos/pagos, congelar operaciones externas desde los controles autorizados; no borrar ni restaurar.
4. Registrar versión, SHA, hora Madrid, ruta y síntoma sin PII.
5. Abrir Sentinel/AutoPilot y obtener el prompt del caso.
6. Comprobar el rollback disponible antes de cualquier cambio.

## Escalado

- DB, persistencia, secretos, cobros o privacidad: aprobación humana obligatoria.
- Telegram real, deploy y rollback: dos comprobaciones y autorización del propietario.
- Datos stale: modo seguro al cliente; no relajar filtros.

## Cierre

Exigir evidencia post-corrección, monitorización y actualización del runbook. Estado actual: **NO CERTIFICADO** hasta que una segunda persona complete un simulacro supervisado.
