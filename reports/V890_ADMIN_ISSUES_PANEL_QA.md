# V890/V892 Admin Issues Panel QA

Panel creado: `/admin/sentinel-issues`.

Validaciones de diseno:

- Admin sobrio, sin navegacion cliente.
- KPIs de abiertas, criticas, altas y Codex Ready.
- Filtros por todas, criticas, abiertas y Codex Ready.
- Buscador por texto.
- Tabla con scroll horizontal controlado.
- Cards de prioridad alta.
- Botones para copiar fallo, prompt, evidencia y checklist.
- Links reales a JSON y ruta afectada si existe.

Integraciones:

- AutoPilot enlaza a `Ver Centro de Incidencias`.
- Visual Worker enlaza a `Enviar hallazgos a Incidencias`.

No se declaran capturas ni pixel-perfect en esta version.
