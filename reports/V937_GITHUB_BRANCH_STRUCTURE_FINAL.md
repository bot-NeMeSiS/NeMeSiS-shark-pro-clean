# V937 GitHub Branch Structure Final

Fecha de cierre: 2026-07-15 (Madrid)

## Decision ejecutiva

- `SHARK PR GATE`: `BLOCKED`.
- `SHARK PRODUCTION GATE`: `NOT_DEPLOYED`.
- `BRANCH CLEANUP GATE`: `PARTIAL`.

La rama SHARK esta publicada, sincronizada y validada localmente, pero GitHub no permitio crear el pull request: el conector devolvio `403 Resource not accessible by integration`. No se ha saltado la aprobacion humana, no se ha tocado `main`, no se ha desplegado y no se ha borrado ninguna rama.

## Estructura operativa

| Familia | Uso | Estado |
|---|---|---|
| `main` | Unica rama oficial de produccion | Conservar siempre |
| `hotfix/*` | Correcciones activas y temporales | Conservar mientras tengan PR, commits unicos o certificacion pendiente |
| `feature/*` | Funciones activas y temporales | No hay ramas activas de esta familia |
| `backup/*` | Rollback y snapshots importantes | Conservar los backups designados; revisar antes de eliminar intermedios |
| `chatgpt/*` | Trabajo historico ya integrado | Limpiar gradualmente solo despues de certificar SHARK |

## Ramas que Damian debe considerar importantes

1. `main` en `261213048fe3f92a58488b1119092922cdfc5db5`.
2. `hotfix/v937-shark-performance` en `8ccf38e3cc4034d73648762489735a62640848eb`.
3. `hotfix/v937-github-render-deployment-pipeline` en `aabb26d67589953c6c2e3ace872469dff45daad7`, con PR `#1` abierto y separado.
4. `backup/pre-v937-production` como snapshot remoto de largo alcance.
5. `backup/pre-v937-live-evidence-gate-20260714` local en `c578199` como rollback solicitado.
6. `backup/pre-v937-diamond-production` remoto en `6844f08`; su referencia local no coincide y requiere revision manual antes de cualquier cambio.

Las ramas `chatgpt/*`, `hotfix/v937-production-certification` y los backups intermedios ya contenidos en `main` se pueden ignorar en la operacion diaria. Siguen conservadas hasta completar la certificacion de produccion y comprobar que no tienen PR ni uso de rollback.

## Revision del hotfix SHARK

- Diff: 18 archivos; cambio funcional concentrado en `app.py` y el guard de `templates/base.html`; test, benchmark y evidencia asociados.
- Sin cambios en Stripe, Telegram, esquema DB, datos deportivos, version, assets comerciales o estilos.
- Compile: PASS.
- Jinja: 182 templates, PASS.
- SHARK fallback, no hallucination, membresia, partido y pick: PASS.
- SQLite moderno, legacy, vacio y bloqueado: PASS.
- Realtime live, cuotas y ciclo de partidos: PASS.
- V937 Sports Lifecycle: PASS.
- Sentinel: 10.0, 0 incidencias, 664 rutas y 929 enlaces sin roturas.
- Imports/routes: PASS, 625 rutas verificadas, sin templates o assets ausentes.
- Secret Guard equivalente V902B: PASS.
- Browser QA reducido nuevo: 10/10 capturas, 0 overflow, 0 error interno y 0 error de navegador.
- Benchmark final de revision: primera carga 46.6 ms; mediana 40.6 ms; p95 69.9 ms; minimo 31.8 ms; maximo 95.5 ms; 6 lecturas DB; 0 escrituras por GET; 0 llamadas externas; 44,606 bytes.

El check historico `check_v935_pick_lifecycle.py` conserva un fallo previo por duplicar el estado `PUBLISHED` en su fixture. Los archivos V935 implicados no difieren de `origin/main`, por lo que no es una regresion SHARK y no se corrige dentro de este hotfix. Dos tests historicos adicionales esperan la version V717 y una configuracion Cron antigua; tambien pertenecen al baseline y no al diff SHARK.

## GitHub y produccion

- PR SHARK encontrado: no.
- Intento de creacion automatica: bloqueado por GitHub con `403`.
- Workflow runs asociados al commit SHARK: ninguno, porque no existe PR.
- PR `#1` de pipeline: abierto, mergeable, no draft y no fusionado.
- SHA de `origin/main`: `261213048fe3f92a58488b1119092922cdfc5db5`.
- SHA de la rama SHARK: `8ccf38e3cc4034d73648762489735a62640848eb`.
- SHA servido por Render: `261213048fe3f92a58488b1119092922cdfc5db5`.
- Runtime Render: V937, archivos alineados, cache busting activo, `NEMESIS_CACHE_V937`, Sentinel 0.
- Datos deportivos: proveedor configurado/disponible, cache activo y ultima sincronizacion segura observada el 2026-07-15 a las 22:00:16 Madrid.
- Deploy SHARK: no realizado.
- Rendimiento SHARK en produccion: no certificado; solo esta demostrado localmente.

## Limpieza aplicada

- Ramas eliminadas: 0.
- Tags eliminados: 0.
- Proteccion de `main` modificada: no.
- Force push: no.
- DB, Telegram o Stripe: no tocados.

La limpieza queda condicionada al merge normal, deploy y certificacion de SHARK. El inventario completo y las candidatas estan en `reports/V937_GITHUB_BRANCH_INVENTORY_AND_CLEANUP_PLAN.md`.

## Unica accion siguiente

Abrir la comparacion autenticada:

`https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean/compare/main...hotfix/v937-shark-performance?expand=1`

Crear el PR con titulo `Hotfix V937 SHARK render performance`, obtener una aprobacion humana y hacer merge normal. Solo despues se debe esperar Render Auto-Deploy, certificar el SHA nuevo y `/shark`, y ejecutar la limpieza condicionada de ramas.
