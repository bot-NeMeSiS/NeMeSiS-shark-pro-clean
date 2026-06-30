# V871 Release Cleanliness QA

## Política preservada
El build limpio mantiene exclusiones de V870 PRO MAX:
- `.git`
- `.venv`
- `__pycache__`
- `.pytest_cache`
- DB local, WAL, SHM y journals
- logs
- ZIPs internos
- `release_output` dentro del ZIP
- vídeos y temporales
- secretos reales
- carpetas anidadas o caches basura

## Validación
El ZIP final se audita con `tools/audit_release_zip.py`.

## Criterio
Debe terminar con `forbidden_count=0` y `missing_required_root=[]`.

## Resultado final
La auditoría final del ZIP V871 terminó con `forbidden_count=0` y `missing_required_root=[]`.
