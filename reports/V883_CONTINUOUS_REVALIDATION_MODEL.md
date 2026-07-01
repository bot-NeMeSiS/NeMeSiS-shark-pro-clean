# V883 Continuous Revalidation Model

El worker puede clasificar cada incidencia como:

- Issue nuevo.
- Issue recurrente.
- Issue resuelto.
- Pendiente de deploy.
- Pendiente de validacion Render.
- Pendiente de browser QA.
- Pendiente de datos reales.
- Bloqueado por credenciales.
- Bloqueado por API/proveedor.

La revalidacion esperada es:

1. Detectar.
2. Clasificar.
3. Agrupar.
4. Crear tarea.
5. Generar prompt Codex.
6. Aplicar fix con aprobacion si procede.
7. Ejecutar checks.
8. Revalidar local.
9. Revalidar Render/browser si aplica.
