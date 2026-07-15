# V937 GitHub Branch Inventory and Cleanup Plan

Fecha de inventario: 2026-07-15 (Madrid)

## Resumen ejecutivo

- Repositorio: `bot-NeMeSiS/NeMeSiS-shark-pro-clean`.
- Rama oficial: `main` en `261213048fe3f92a58488b1119092922cdfc5db5`.
- Ramas locales: 16.
- Ramas remotas reales: 16 (se excluye el alias `origin/HEAD`).
- PR abiertos: 1, correspondiente a `hotfix/v937-github-render-deployment-pipeline`.
- PR para `hotfix/v937-shark-performance`: no existe en GitHub en el momento del inventario.
- Ramas eliminadas: 0.

No se debe borrar ninguna rama hasta que el hotfix SHARK este fusionado, desplegado y certificado en Render.

## Inventario remoto

Los campos `ahead` y `behind` se calculan contra `origin/main`. `merged=yes` significa que la rama no contiene commits unicos fuera de `main`.

| Rama | SHA corto | Fecha | Ahead | Behind | Merged | Clasificacion | Proposito y recomendacion |
|---|---|---:|---:|---:|---|---|---|
| `main` | `2612130` | 2026-07-14 21:43 | 0 | 0 | yes | MAIN | Unica rama oficial de produccion. Conservar siempre. |
| `hotfix/v937-shark-performance` | `8ccf38e` | 2026-07-15 17:14 | 1 | 0 | no | ACTIVE_HOTFIX | Hotfix SHARK validado localmente. Conservar, crear PR, revisar y fusionar normalmente. Riesgo critico si se borra antes del merge. |
| `hotfix/v937-github-render-deployment-pipeline` | `aabb26d` | 2026-07-15 02:42 | 10 | 0 | no | ACTIVE_HOTFIX | PR #1 abierto; contiene 10 commits unicos de pipeline/CI. Mantener y revisar separadamente. No mezclar con SHARK. |
| `hotfix/v937-production-certification` | `f3feba6` | 2026-07-14 21:42 | 0 | 1 | yes | MERGED_SAFE_TO_DELETE | Hotfix live evidence ya integrado. Candidata a borrar solo tras certificar SHARK y confirmar que no es rollback activo. |
| `chatgpt/v937-diamond-product-brand-business-final` | `36db4f2` | 2026-07-14 17:47 | 0 | 6 | yes | MERGED_SAFE_TO_DELETE | Trabajo Diamond ya integrado. Candidata a limpieza posterior. |
| `chatgpt/v937-product-perfection` | `58cb64d` | 2026-07-13 07:55 | 0 | 23 | yes | MERGED_SAFE_TO_DELETE | Candidata V937 ya integrada. Candidata a limpieza posterior. |
| `backup/pre-v937-production` | `6dafad2` | 2026-07-12 11:14 | 0 | 30 | yes | BACKUP_KEEP | Snapshot preproduccion historico. Conservar como rollback de largo alcance. |
| `backup/pre-v937-diamond-production` | `6844f08` | 2026-07-14 07:30 | 0 | 7 | yes | BACKUP_KEEP | Snapshot remoto previo a Diamond. Conservar; el puntero local del mismo nombre no coincide y requiere revision manual. |
| `backup/pre-v937-live-board-stale-guard-20260713` | `5e41e1e` | 2026-07-13 21:00 | 0 | 12 | yes | MERGED_SAFE_TO_DELETE | Snapshot intermedio ya contenido en main. Candidata posterior. |
| `backup/pre-v937-live-freshness-badge-20260713` | `464d400` | 2026-07-13 21:23 | 0 | 10 | yes | MERGED_SAFE_TO_DELETE | Snapshot intermedio ya contenido en main. Candidata posterior. |
| `backup/pre-v937-live-state-merge-20260713` | `2af6320` | 2026-07-13 21:14 | 0 | 11 | yes | MERGED_SAFE_TO_DELETE | Snapshot intermedio ya contenido en main. Candidata posterior. |
| `backup/pre-v937-render-performance-20260713` | `7113a8f` | 2026-07-13 18:22 | 0 | 16 | yes | MERGED_SAFE_TO_DELETE | Snapshot intermedio de rendimiento ya contenido en main. Candidata posterior. |
| `backup/pre-v937-shared-cron-hotfix-20260713` | `252bda3` | 2026-07-13 16:46 | 0 | 17 | yes | UNKNOWN_MANUAL_REVIEW | Commit y mensaje poco descriptivos (`fhg`). Aunque esta fusionada, revisar trazabilidad antes de borrar. |
| `backup/pre-v937-sports-read-order-20260713` | `306268b` | 2026-07-13 19:32 | 0 | 14 | yes | MERGED_SAFE_TO_DELETE | Snapshot intermedio ya contenido en main. Candidata posterior. |
| `backup/pre-v937-stale-live-guard-20260713` | `6e4bff4` | 2026-07-13 20:35 | 0 | 13 | yes | MERGED_SAFE_TO_DELETE | Snapshot intermedio ya contenido en main. Candidata posterior. |
| `backup/pre-v937-summary-cache-20260713` | `ab65359` | 2026-07-13 19:09 | 0 | 15 | yes | MERGED_SAFE_TO_DELETE | Snapshot intermedio ya contenido en main. Candidata posterior. |

## Estado local especial

- `backup/pre-v937-live-evidence-gate-20260714` existe solo localmente en `c578199`, esta contenido en `main` y debe conservarse como rollback solicitado hasta completar la certificacion.
- La rama local `backup/pre-v937-diamond-production` apunta a `2612130`, mientras la remota del mismo nombre apunta a `6844f08`. No se debe mover ni borrar ninguna de las dos sin decidir cual representa el rollback esperado.
- `backup/pre-v937-production` existe solo como referencia remota; es un backup importante y debe conservarse.

## Pull requests

| PR | Estado | Rama | SHA | Accion |
|---|---|---|---|---|
| `#1` | OPEN, no draft | `hotfix/v937-github-render-deployment-pipeline` | `aabb26d` | Mantener abierto y revisar sus 10 commits unicos por separado. No esta fusionado. |
| SHARK | NO CREADO | `hotfix/v937-shark-performance` | `8ccf38e` | Crear PR real hacia `main`; no duplicar si aparece uno durante el proceso. |

## Plan de limpieza condicionado

1. Crear, revisar y fusionar mediante merge normal el PR SHARK.
2. Confirmar que `origin/main` cambia y que Render sirve el nuevo SHA.
3. Certificar `/shark` con al menos 10 mediciones, Browser QA y Sentinel.
4. Revisar el PR #1 de pipeline de forma independiente; no asumir que esta fusionado.
5. Conservar `main`, `backup/pre-v937-production`, `backup/pre-v937-live-evidence-gate-20260714` y el backup remoto pre-Diamond.
6. Eliminar solo las ramas `MERGED_SAFE_TO_DELETE` que sigan sin PR abierto, sin commits unicos y sin uso como rollback.
7. Dejar `UNKNOWN_MANUAL_REVIEW` intacta hasta resolver su trazabilidad.

## Gate actual

- Branch inventory: PASS.
- SHARK PR: BLOCKED por falta de permiso de escritura de la integracion GitHub y ausencia de sesion autenticada en el navegador disponible.
- Branch cleanup: BLOCKED hasta certificacion de produccion.

