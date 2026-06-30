# V870 Workspace Full Tree and Hidden Files Audit

## Alcance
Auditoría local de la carpeta oficial `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`. No se borró nada a ciegas.

## Resumen cuantitativo
- Archivos detectados: 11.269.
- ZIPs locales detectados: 72.
- DB/SQLite/WAL/SHM/journal detectados: 63.
- Logs detectados: 0.
- Media pesada detectada en carpeta del proyecto: 0.
- Carpetas `__pycache__`: 109.
- Carpetas `.pytest_cache`: 1.
- ZIPs en `release_output`: 72.

## Carpetas principales
| Carpeta | Clasificación | Observación |
|---|---|---|
| `app.py`, `templates`, `static`, `engines`, `tools` | CRÍTICO | Núcleo de aplicación y release. |
| `reports` | ÚTIL LOCAL | Informes de QA; se permiten selectivamente por versión en release. |
| `.git` | ÚTIL LOCAL / RELEASE-BLOCKER | Necesario para desarrollo, nunca en ZIP. |
| `.venv` | ÚTIL LOCAL / RELEASE-BLOCKER | Necesario local, nunca en ZIP. |
| `release_output` | ÚTIL LOCAL / RELEASE-BLOCKER | Guarda ZIPs históricos; nunca se incluye en un ZIP. |
| `data` | PELIGROSO | Puede contener DB local; nunca entra al release. |
| `v636work` | LEGACY / RELEASE-BLOCKER | Carpeta histórica; no debe entrar al release. |
| `__pycache__`, `.pytest_cache`, `tmp` | BASURA SEGURA | Excluir siempre. |

## Riesgo real
La carpeta de trabajo tiene bastante historia acumulada. El riesgo no es el ZIP Render Ready actual si se usa `build_clean_release.py`; el riesgo es copiar manualmente la carpeta completa o usar ZIPs antiguos como base.

## Decisión V870 PRO MAX
- No borrar `.git`, `.venv`, DBs ni ZIPs históricos automáticamente.
- Reforzar exclusiones y auditoría.
- Documentar qué puede archivarse manualmente.
- Mantener `forbidden_count=0` como criterio de salida.
