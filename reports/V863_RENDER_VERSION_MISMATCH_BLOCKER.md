# V863 Render Version Mismatch Blocker

## Estado

No hay mismatch contra la base previa V862: Render devuelve `V862_CONTINUOUS_SHARK_SENTINEL_AUTO_IMPROVEMENT_LOOP_FINAL`.

Sí hay bloqueo para certificar V863 en producción: el deploy V863 no se ha ejecutado, por decisión de seguridad y porque el prompt prohíbe deploy automático sin aprobación.

## Acción siguiente

1. Subir el contenido de la V863 a GitHub o al método de despliegue acordado.
2. Ejecutar deploy autorizado en Render.
3. Verificar `https://bot-apuestas-crgf.onrender.com/api/runtime-version`.
4. Certificar producción solo si devuelve `V863_REAL_WORLD_FULL_APP_CERTIFICATION_MAX_QA_FINAL`.
