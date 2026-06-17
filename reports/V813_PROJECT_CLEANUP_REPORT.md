# V813 Project Cleanup Report

## Política de limpieza

No se eliminaron módulos funcionales ni plantillas reales. V813 se apoya en el sistema de release limpio existente para excluir basura del ZIP final sin destruir historial útil de trabajo en la carpeta oficial.

## Excluido del ZIP por política

- `.git/`
- `.venv/`, `venv/`, `env/`
- `__pycache__/`
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- `release_output/`, `releases/`
- `logs/`, `backups/`, `tmp/`, `temp/`
- bases de datos locales `.db`, `.sqlite`, `.sqlite3`, WAL/SHM
- vídeos locales `.mp4`, `.mov`, `.avi`, `.mkv`
- ZIPs internos
- archivos con nombres sensibles salvo `.env.example` y `.env.render.clean`

## Duplicados y legado

Se detectó que la carpeta oficial conserva documentación histórica y herramientas de versiones anteriores. No se borró porque parte de esa documentación sirve como trazabilidad comercial y técnica. El ZIP final queda controlado por allowlist/exclusiones, de modo que no arrastra bases locales, vídeos, cachés ni ZIPs internos.

## Cambios de limpieza V813

- `tools/build_clean_release.py` ahora incluye informes V812/V813 y auditorías `RELEASE_ZIP_AUDIT_V812/V813` dentro del release limpio.
- Se añadieron checks V813 bajo `tools/` para bloquear rutas/enlaces rotos y regresiones de lifecycle/Telegram.

## Revisión manual pendiente

- La documentación histórica antigua puede moverse a archivo documental en una versión futura, pero no se recomienda borrarla sin una decisión explícita.
