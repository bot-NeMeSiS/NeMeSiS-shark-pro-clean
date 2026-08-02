# Release 1.0 Commit Manifest

Fecha Madrid: 2026-08-02 20:35 +02:00

## Estado inicial

| Campo | Valor |
| --- | --- |
| Rama | `main` |
| HEAD inicial | `040253ba1642ad564dba5892f0edcb949dfa9ce5` |
| origin/main | `040253ba1642ad564dba5892f0edcb949dfa9ce5` |
| Ahead/behind inicial | `0 0` |
| Working tree inicial | limpio |
| Staging inicial | vacio |
| Untracked inicial | ninguno visible |

## Diff acumulado revisado

No habia diff acumulado en el working tree al comenzar el cierre. Por tanto:

- no existen archivos tracked modificados que atribuir;
- no existen eliminaciones locales;
- no existen archivos untracked visibles;
- no existen commits locales ahead de `origin/main`;
- no existe staging previo;
- no hay cambios compartidos entre sprints que separar por hunk.

## Archivos candidatos al commit documental

| Archivo | Categoria | Debe entrar | Motivo |
| --- | --- | --- | --- |
| `reports/RELEASE_1_BASELINE_CLOSURE_REPORT.md` | Documentacion Release 1.0 | SI | Informe principal del cierre |
| `reports/RELEASE_1_COMMIT_MANIFEST.md` | Documentacion Release 1.0 | SI | Manifiesto de estrategia Git |
| `reports/RELEASE_1_QA_CERTIFICATION.md` | Documentacion Release 1.0 | SI | Evidencia QA local |
| `reports/RELEASE_1_PENDING_EXTERNAL_GATES.md` | Documentacion Release 1.0 | SI | Gates externos no certificados |

## Archivos excluidos

| Ruta | Categoria | Motivo |
| --- | --- | --- |
| `backups/RELEASE_1_BASELINE_CLOSURE_20260802T201528+0200/` | Backup local ignorado | Evidencia de seguridad, no release |
| `tmp/browser_qa_release_1_baseline_closure/` | Browser QA temporal | Evidencia regenerable ignorada |
| `tmp/pytest_release_baseline/` | Runtime temporal de tests | Basetemp ignorado |
| `.pytest_cache/` | Cache | Ignorada; no entra en release |
| `data/runtime/not_found_events.json` | Runtime regenerable | Tocado por QA y restaurado a HEAD |
| `data/runtime/sentinel_issues_memory.json` | Runtime regenerable | Tocado por QA y restaurado a HEAD |

## Plan de commits

No corresponde crear commits funcionales porque la base estaba limpia.

Commit unico propuesto:

```text
docs(release): close Release 1.0 baseline

- document clean Git baseline for Release 1.0
- record verified backup and QA evidence
- classify external gates that remain outside local Git closure
- exclude runtime, caches, Browser QA temporaries and backups from release
- no production, push, deploy, Telegram, Stripe or Sports Core changes
```

## Staging selectivo

Regla:

- no usar `git add .`;
- no usar `git add -A`;
- stagear exclusivamente los cuatro informes de `reports/RELEASE_1_*`.

## Hashes

El hash final del commit documental debe registrarse despues de ejecutar el commit y verificarse con:

```text
git log --oneline --decorate -20
git status --short
git rev-list --left-right --count HEAD...origin/main
```

Motivo: un documento no puede contener de forma estable el hash del mismo commit que lo contiene sin cambiar su contenido.
