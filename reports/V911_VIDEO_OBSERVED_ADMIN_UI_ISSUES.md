# V911 Video Observed Admin UI Issues

Version: `V911_VIDEO_ADMIN_UI_BINDING_BROWSER_QA_QUEUE_FIX_FINAL`

## Evidence

El video indicado (`NeMeSiS SHARK PRO - Google Chrome 2026-07-08 00-56-14.mp4`) no estaba disponible como archivo local en las rutas accesibles del workspace. La auditoria usa la descripcion enviada por el usuario como evidencia directa del video.

## Issues observed

- `/admin/shark-sentinel` mostraba una percepcion de mezcla cliente/admin por el footer del rail: `Vista cliente` junto a `Salir`.
- La separacion entre navegacion cliente y admin necesitaba un guard mas estricto en el shell base.
- Cards KPI en Browser QA/Sentinel podian leerse pegadas, por ejemplo `Capturas0desktop/mobile` y `Comparaciones18reference_images`.
- El panel de Render mostraba `Local` y `Render: No consultado` de forma confusa.
- Browser QA y Visual Fix Queue seguian bloqueados por falta de screenshots reales.
- El admin necesitaba un contrato visual mas compacto y profesional para comportarse como command center.

## Decision

Aplicar correcciones seguras de UI/admin sin tocar datos, secretos, pagos, Telegram real, DB ni deploy.
