# V905 Next Steps

1. Subir el contenido de `release_output/V905_DEPLOY_ROOT_CONTENTS` a la raíz del repo GitHub.
2. Confirmar en GitHub que `VERSION.txt` no tiene BOM y contiene V905.
3. Confirmar `app.py` con `APP_VERSION` V905.
4. En Render ejecutar Manual Deploy con Clear build cache.
5. Consultar `/api/runtime-version`.
6. Confirmar:
   - `version_files_match=true`.
   - `deployment_alignment_status=aligned_local_files`.
   - `has_v905_bom_version_alignment_fix=true`.
7. Ejecutar Browser QA real y comparar contra las 16 imágenes de referencia.
