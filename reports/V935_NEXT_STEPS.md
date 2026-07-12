# V935 Next Steps

## Estado de salida

- Release local: `V935_LAUNCH_TRUST_REAL_DATA_LIFECYCLE_PERFORMANCE_REFERENCE_POLISH_FINAL`.
- Datos deportivos inventados: no.
- Operaciones reales de pagos o Telegram: no ejecutadas.
- Push y deploy: no ejecutados.
- Pixel-perfect: no declarado; las capturas requieren validación humana final.

## Despliegue

1. Subir el contenido interno de `release_output/V935_DEPLOY_ROOT_CONTENTS` a la raíz de `main`.
2. Confirmar que `app.py`, `VERSION.txt`, `requirements.txt`, `templates/`, `static/`, `engines/`, `tools/` y `automation_workforce/` quedan en la raíz, no dentro de una carpeta padre.
3. Esperar el auto-deploy de Render o iniciar el deploy autorizado desde Render.
4. Consultar `https://bot-apuestas-crgf.onrender.com/api/runtime-version` hasta obtener V935, `version_files_match=true` y `deployment_alignment_status=aligned_local_files`.
5. Ejecutar el smoke post-deploy y revisar Data Trust Center, calendario, live, picks, histórico, dashboard admin y tiempo real.

El runtime externo no pudo consultarse desde esta sesión por una restricción de seguridad del navegador. La confirmación post-deploy es obligatoria y V935 no se considera producción hasta obtenerla.

## Datos reales

La base local de QA no contiene una agenda deportiva evaluable. En el entorno autorizado, ejecutar la sincronización protegida y comprobar en Data Trust Center la procedencia, última sincronización, lifecycle, frescura de cuotas e incidencias antes de publicar contenido.
