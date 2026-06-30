# Daily Next Actions 2026-06-30

## Próximo avance sugerido
- Versión: `V866_SENTINEL_COPY_VISUAL_REVIEW_AND_ADMIN_WORKFLOW_QA_FINAL`.
- Objetivo: revisar visualmente los 19 hallazgos low del Sentinel y cerrar falsos positivos o corregir texto técnico visible.
- Prioridad: alta, porque afecta confianza comercial y percepción premium.

## Acciones concretas
- Ejecutar browser QA en `/`, `/cliente-login`, `/registro`, `/support`, `/partidos`, `/calendar`, `/live`, `/directo`, `/picks`, `/shark`, `/track-record`.
- Actualizar checks antiguos V864/V863 para aceptar V865+ cuando validen preservación histórica.
- Investigar warning de ruta duplicada `/admin/client-screens`.
- Revisar endpoints legacy esperados por smoke y decidir si se restauran o se actualiza el smoke.
- Validar V865 en Render real antes de cualquier deploy.

## No tocar sin autorización
- Secretos.
- DB real.
- Usuarios.
- Pagos reales.
- Envío Telegram real.
- Deploy/push automático.
