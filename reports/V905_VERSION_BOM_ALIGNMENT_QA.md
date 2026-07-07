# V905 Version BOM Alignment QA

## Causa

Render V904 devolvia `version_files_match=false` porque `VERSION.txt` contenia un BOM UTF-8 visible como `\ufeff` antes de la version.

## Correccion

- `VERSION.txt` fue reescrito sin BOM.
- `APP_VERSION` fue actualizado a `V905_FINAL_REFERENCE_GAPS_BROWSER_QA_AND_BOM_FIX_FINAL`.
- `app.py` fue actualizado a la misma version.
- `/api/runtime-version` ahora usa `clean_version_text(value)` para comparar versiones saneadas.

## Resultado esperado local

- `version_txt = V905_FINAL_REFERENCE_GAPS_BROWSER_QA_AND_BOM_FIX_FINAL`.
- `app_version = V905_FINAL_REFERENCE_GAPS_BROWSER_QA_AND_BOM_FIX_FINAL`.
- `runtime_version = V905_FINAL_REFERENCE_GAPS_BROWSER_QA_AND_BOM_FIX_FINAL`.
- `version_files_match = true`.
- `deployment_alignment_status = aligned_local_files`.

## Render

No se declara V905 en produccion hasta que Render devuelva V905 y `version_files_match=true`.
