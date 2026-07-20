# V938 Operations Center - Preflight

Fecha de corte: 2026-07-20 (Europe/Madrid)

## Identidad confirmada

- Estado: **CONFIRMADO**
- Carpeta oficial: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`
- Base real local: `V937_PRODUCT_PERFECTION_FULL_ECOSYSTEM_LAUNCH_CLOSEOUT_FINAL`
- Rama local detectada por `.git/HEAD`: `hotfix/v937-shark-performance`
- SHA local detectado: `3102618e22c00b0140e8db761adc9b42f1e50b4a`
- Versión objetivo: `V938_COMPANY_OPERATIONS_RECOVERY_OBSERVABILITY_CENTER_FINAL`
- No se usa V890 ni una copia anterior como base.
- No se ha consultado, modificado ni desplegado producción durante este preflight.

## Estado Git preservado

Tras localizar el runtime Git incluido en el entorno, la identidad se confirmó con Git de solo lectura:

- Rama: `hotfix/v937-shark-performance`.
- SHA: `3102618e22c00b0140e8db761adc9b42f1e50b4a`.
- `git diff --check`: **PASS**.
- No se ejecutó fetch, push, merge, commit ni ninguna operación remota.
- GitHub y Render continúan **BLOQUEADOS POR ACCESO** para certificación remota; esto no se interpreta como fallo.

Cambios rastreados que ya existían antes de V938 y deben preservarse:

- `data/runtime/not_found_events.json`
- `data/runtime/sentinel_issues_memory.json`

El índice contiene 8.850 entradas rastreadas, no se detectaron eliminaciones rastreadas y existen archivos no rastreados previos, incluidos informes de auditoría empresarial y evidencias Browser QA históricas. V938 no revertirá ni sobrescribirá esos cambios.

## Diferencias locales pendientes

- **CONFIRMADO:** dos memorias runtime rastreadas están modificadas.
- **CONFIRMADO:** existen informes `COMPANY_*.md` y `COMPANY_AUDIT_MANIFEST.json` no rastreados que aportan evidencia a V938.
- **REQUIERE REVISIÓN:** el gran volumen de artefactos Browser QA e informes históricos no se elimina en esta versión; la limpieza no forma parte del Operations Center y no se hará sin demostrar que un archivo está fuera de runtime, build y pruebas.
- **BLOQUEADO POR ACCESO:** no se certifica el estado remoto de GitHub ni el SHA de Render desde este preflight local.

## Checks disponibles

Se han localizado, entre otros:

- `tools/check_madrid_times.py`
- `tools/check_v887_telegram_queue_skipped_hotfix.py`
- `tools/check_v888_sentinel_autopilot.py`
- `tools/check_v915_automated_company_workforce.py`
- `tools/run_continuous_sentinel_static.py`
- `tools/verify_imports_and_routes.py`
- `tools/audit_all_routes_links.py`
- `tools/build_clean_release.py`
- `tools/audit_release_zip.py`

V938 añadirá un check específico sin sustituir los checks históricos. Si un check histórico exige una identidad antigua en vez de compatibilidad, se documentará como expectativa obsoleta y no se fingirá un PASS.

## Restricciones operativas

- Producción, GitHub y Render: solo quedan como **NO CERTIFICADO** o **BLOQUEADO POR ACCESO**.
- DB real: no se escribirá, reemplazará, restaurará ni migrará.
- Telegram real: no se enviará ningún mensaje.
- Stripe: no se iniciará checkout, pago, portal ni webhook real.
- Secretos: solo se comprobará presencia de nombres o patrones; nunca se mostrarán valores completos.
- Backups: se auditarán metadatos y diseño; cualquier restore se limitará a una copia aislada de prueba.

## Gate de entrada

**PASS LOCAL CON LIMITACIONES.** La base V937 y el SHA local están identificados; el árbol previo queda preservado; V890 queda expresamente excluida; se puede iniciar V938 de forma local y no destructiva.
