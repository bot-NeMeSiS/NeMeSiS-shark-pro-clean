# NeMeSiS Reconciliation Audit

## Cierre activo de consolidacion - 2026-10-02

Estado al registrar este cierre: CANDIDATA PENDIENTE DE VALIDACION REMOTA.
Este apartado sustituye las reglas
operativas de julio conservadas al final como historia, incluida su antigua
instruccion de trabajar directamente en main.

### Identidad y limites

- Base comprobada: `cc1481c0a29f91be49f92abaaea48e3dde345356`.
- Unica rama candidata: `codex/consolidation-20261001`.
- Unica PR de consolidacion: #142, OPEN/DRAFT; sin auto-merge.
- Coordinadora identificada y fijada; ningun agente escritor nuevo.
- Continuidad canonica: `project_control/CURRENT_TRUTH.md`.
- Sin merge a main, deploy, cambio operativo, proveedor ni datos reales.
- La publicacion de una PR de consolidacion esta autorizada, no su fusion.
  Workflows inspeccionados: PR ejecuta pruebas/preflight; la certificacion
  productiva se reserva a push main o dispatch explicitamente autorizado.

### Procedencia y destino

| Origen | Decision y destino |
| --- | --- |
| Main / #141 | Base completa. Conservar recuperacion pospartido, derechos y POST/303/GET. |
| #139 | Merge controlado sin conflictos; corregidos eventos decisivos y editorial ES/EN/FR. |
| #134 | Reutilizado inventario de 35 ramas; inspector/tests recuperados sin sus workflows puntuales. Reemplazos Git no pueden falsear ascendencia. |
| #137/#138 | Ya representados en main; no repetir la recuperacion. |
| #135 | Solo seguridad de publicacion recuperada. Modelo y calibracion incompletos preservados fuera. |
| #136 | Incidencia OPEN, no PR. Presupuesto SportsDB requiere adaptacion propia conservando frescura, candidatos stale y conteo real. No activado aqui. |
| Sentinel local | Cache-Control privado reparado sin cambiar reconocimiento/generacion de alertas. Original intacto. |
| Admin local | Aislamiento de cache PWA recuperado; fiabilidad/copiloto/RC preservados pendientes por cambio de contratos no certificado. |
| Navegacion local | Enlaces de errores, recarga local y etiqueta Hoy recuperados. Retencion de plantillas blueprint adaptada; heuristicas experimentales restantes preservadas. |
| PWA local antigua | No sustituir el manejo actual de instalacion/guia por listeners antiguos. Comparacion de contenido, no preferencia por fecha. |
| Design / release documental | Commits, modificaciones y eliminaciones preservados. No importar borrados ni workflows obsoletos. |
| Telegram historico | Original preservado; main contiene avances posteriores de delivery/budgets. No restablecer la revision antigua. |
| Reparacion #92 / provider review | Historial preservado; comparar con main ya integrado, no repetir el sprint. |

### Reparaciones y evidencia

- Eventos decisivos seleccionados antes de truncar a cuatro, manteniendo orden
  cronologico y los nombres canonicos de gol, roja, segunda amarilla y penaltis.
- Editorial usa el catalogo existente y el idioma real del request; conserva
  identidades y narrativa externa. No equivale a certificar toda la app EN/FR.
- Publicacion automatica requiere `can_publish is True`, decision BET y cuota
  finita mayor que uno. WAIT/NO_BET y booleanos no se transforman en picks.
- Cache privada comprueba directivas HTTP, no subcadenas; `public, no-store`
  no puede quedar como respuesta administrativa publica.
- Service worker solo retira caches propias `NEMESIS_CACHE_`; no borra las
  de otras aplicaciones del mismo origen ni almacena respuestas privadas.
- Dependencia Windows `tzdata==2026.2` declarada para Europe/Madrid en un
  entorno limpio. No cambia dependencias Linux ni offsets deportivos.
- QA de Windows corrige cierre real de conexiones SQLite y nombres de casos
  XML demasiado largos; no rebaja datos ni aserciones.
- Launcher LOCAL SAFE entregaba listas de caracteres al guard nuevo. Ahora
  entrega argv estructurado; se conserva la validacion estricta de ejecutable,
  argumentos y red. Replay/admin/Telegram reales locales pasan con el guard activo.
- Sentinel confundia cuatro controles desactivados y seis endpoints relativos
  con acciones rotas. Se conserva evidencia/aviso contextual y se prueban
  tambien boton habilitado sin accion y endpoint inexistente, que siguen fallando.

### Validacion de la revision

Codigo integrado en `df813446` (merge #139, padre `8aa7517e`) y
`fd13abd2` (reparaciones recuperadas). Las pruebas se ejecutaron sobre el
checkout completo con esos cambios; la documentacion no cambia sus contratos.
El ultimo SHA de rama/merge temporal y sus checks se verifican en la PR unica
antes de declarar CANDIDATA CONSOLIDADA Y VERIFICADA.

- Linea base main: 94 pruebas pospartido PASS antes de integrar.
- Primera estandar Windows: 3834 casos, 3822 PASS, 12 FAIL, 0 ERROR, 0 SKIP.
  No se declara PASS global. Siete fallos eran lecturas UTF-8 con codec Windows;
  dos comparaban el presupuesto de un fixture del 1/10 con el dia real 2/10;
  uno era geometria Chromium 43.999969 para un control de 44px.
  Se fija encoding/reloj de prueba y se exige min-height >=44 mas tolerancia
  geometrica de 0.0001px. Ningun dato/presupuesto se cambia para obtener verde.
  Los dos restantes requieren Gunicorn/fcntl en Linux; no se omiten ni simulan.
- Regresiones de esas correcciones: 198 PASS. Navegacion/guard: 71 PASS.
  Son ejecuciones relacionadas, no un nuevo total de suite sumando repeticiones.
- LOCAL SAFE/fresh en diez procesos, ultimo resultado de cada grupo:
  replay 10, betting 11, continuidad cliente 1, membresias 13, admin HTTP 106,
  admin browser 100, Telegram visual 74, project control 8, Sentinel HTTP 10,
  Sentinel browser 1: 334 PASS, sin red externa. Los tres grupos inicialmente
  bloqueados por argv Windows se repitieron completos tras reparar el launcher.
- HTTP completo: editorial 36 (FREE/PRO/ELITE/ADMIN x ES/EN/FR x 320/390/1440);
  feed automatico simulado 12; resultados #141 parcial/error/vacio 9.
  Fuente sintetica marcada SIMULATED_QA, Tokyo no altera hora Madrid,
  sin autoplay, cero desbordamiento/errores JS en esas matrices.
- Enlaces de errores admin: clic, detalle, recarga y retorno HTTP a 320/390/1440;
  clientes y anonimo rechazados. No son pruebas de iPhone/PWA instalada.
- 1180 Python compilados en la comprobacion inicial, 198 plantillas Jinja;
  Smoke PASS, Madrid PASS, imports PASS, rutas/enlaces PASS (865 rutas
  registradas, 0 formularios JS sin binding). Nuevos tests tambien compilados
  por pytest. Guard de secretos: 0 hallazgos; clasificacion de privacidad PASS.
- Sentinel quick/static: 39 rutas, 0 incidencias tras corregir el detector,
  sin afirmar perfeccion del producto ni observacion productiva.
- La revision visual confirma traduccion editorial, no toda la aplicacion:
  siguen copys heredados de SHARK/navegacion/etiquetas de recuperacion en ES;
  titulares externos y nombres propios no se traducen artificialmente.
- Evidencias y logs detallados quedan locales/privados o en artifacts CI.
  No se incorporan DB, caches, capturas de cuentas reales ni datos operativos.
- Primer CI en HEAD `c410667e`, merge temporal `6bc09354`: Smoke fallo en
  `test_served_worker_activation_preserves_unrelated_caches`, porque el gate
  rapido precedia a instalar Chromium. Se adelanta la instalacion existente,
  sin omitir ninguna prueba, y se agrega un caso negativo que rechaza ese orden.
  Consultar el ultimo CI de #142; este fallo no se oculta con los PASS locales.

### Sesiones y recuperacion

- Visibilidad: coordinadora activa, una conversacion relacionada inactiva y
  once historicas archivadas del proyecto; no es un total global de sesiones.
- CLI Cloud accesible: cero tareas y sin cursor al consultar. Otras cuentas,
  dispositivos y extension no comprobables.
- Coordinadora renombrada/fijada y verificada. Ninguna sesion pausada/archivada
  por esta mision: no se certifico un archivado sin efectos en archivos ignorados.
- Nueve origenes preservados con refs de recuperacion, parches staged/unstaged
  y copias de 31 archivos de fuente; 300 registros de eliminacion conservados,
  no ejecutados. Revalidacion final: 9 HEAD/status/refs y 331 registros
  seleccionados coinciden; cero cambio conocido en esos originales.
  El inventario original advierte rutas QA historicas largas no enumerables;
  no se afirma respaldo fisico completo ni se autoriza retirarlas.
- Disposiciones privadas por archivo: 9 adaptados/probados, 300 eliminaciones
  no reproducidas, 4 workflows historicos preservados, 13 pendientes acoplados,
  3 cambios de metadata de tests conservados y 2 implementaciones sustituidas
  por el PWA actual. Todo conserva destino y recuperacion; nada se borra.
- Datos ignorados, secretos y DB quedan en sus originales, NO se presentan
  como respaldados por las copias selectivas. No hay autorizacion para retirarlos.
- Inventario de sesiones, hashes, rutas y recovery permanecen privados.
  Los originales siguen disponibles. No publicar transcripciones ni archivos
  privados para demostrar el traspaso.

### Reanudacion minima

Leer este apartado y Current Truth, comprobar HEAD/diff/refs actuales y terminar
la validacion de la unica candidata. Mantener separados: main integrado,
candidata probada, trabajo preservado y produccion observada. No abrir otra
linea de reconstruccion ni reejecutar prompts historicos.

---

## Archivo historico - 2026-07-23 (NO VIGENTE)

Status: IN_PROGRESS
Working branch: `main`
Date: 2026-07-23

## Verified repository state

- Official repository: `bot-NeMeSiS/NeMeSiS-shark-pro-clean`
- Single working branch: `main`
- Declared version in `VERSION.txt`: `V937_PRODUCT_PERFECTION_FULL_ECOSYSTEM_LAUNCH_CLOSEOUT_FINAL`
- Runtime stack: Flask 3.0.3, Gunicorn 22.0.0, Python 3.11.9 on Render.
- Persistent database path: `/data/database.db`.
- Render web service: `nemesis-shark-pro`.
- Sports synchronization cron: every 15 minutes.

## Reconciliation target

Determine the real implementation status of the work described as V940-V944 and reconcile it with GitHub before beginning V945.

## Rules

1. `main` is the single source of truth and the only working branch for normal development.
2. No production or Render changes during reconciliation.
3. No historical version is accepted without code and test evidence.
4. Missing work will be reconstructed in controlled, clearly named commits.
5. Every important change must leave `main` in a recoverable state.
6. Git history is the rollback mechanism; temporary branches are not part of the normal workflow.
7. No deployment is considered complete without smoke validation in Render.

## Audit workstreams

- Repository architecture and entry points.
- Client routes, templates and responsive system.
- Admin routes and operations.
- Sports data and live lifecycle.
- Calendar implementation.
- Match Center contracts and components.
- SHARK, Telegram, memberships and payments.
- Test, QA, Sentinel, AutoPilot and release tooling.
- Runtime version and Render alignment.

## Current findings

1. GitHub read and write access is confirmed.
2. The initial audit record has been incorporated into `main`.
3. `VERSION.txt` still identifies V937.
4. The visible commit history inspected so far also ends in V937 work.
5. V940-V944 remain unverified and must not yet be treated as present in `main`.
6. Future work will be committed directly to `main` with clear, reversible commit messages.

## Next gate

Produce a code-backed inventory and a reconciliation plan before implementing V945.
