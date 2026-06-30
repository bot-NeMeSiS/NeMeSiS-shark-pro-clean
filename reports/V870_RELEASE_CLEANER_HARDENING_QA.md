# V870 Release Cleaner Hardening QA

## Builder
`tools/build_clean_release.py` excluye:
- `.git`, `.venv`, cachés, `release_output`, `releases`, `v636work`.
- DBs, WAL/SHM, logs, vídeos, ZIPs internos, temporales y backups.
- Reportes V869/V870 y auditorías ZIP V869/V870 quedan incluidos de forma explícita sin abrir la puerta a archivos prohibidos.

## Auditor
`tools/audit_release_zip.py` falla si detecta:
- directorios prohibidos;
- DB/log/media runtime;
- ZIP interno;
- nombres sensibles no permitidos;
- raíz obligatoria ausente.

## Refuerzo PRO MAX
- El check V870 PRO MAX verifica exclusiones para `.git`, `.venv`, cachés, DB, `release_output`, `v636work`, vídeos, ZIPs internos, secretos, backups y temporales.
- `.gitignore` añade guardrails PRO MAX para backups, frames y carpetas legacy.
- Criterio de éxito: `forbidden_count=0` y `missing_required_root=[]`.
