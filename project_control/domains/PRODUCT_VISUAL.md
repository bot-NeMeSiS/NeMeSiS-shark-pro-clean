# Product / Visual

Estado vigente: [reconciliacion UX-002/UX-003/QA-002](#reconciliacion-ux-002--ux-003--qa-002).
Las secciones previas conservan sus fechas y limites historicos.

UX-001 BLOCKED por decision humana; sin rediseno en CX-ORG-01.
Design System 1.0 y cambios visuales del candidato se conservan.

## Autoridad y cobertura

- REFERENCE_ONLY: 16 PNG oficiales segun inventario historico. No reabiertas en
  esta higiene; no nueva afirmacion MATCH ni copia de payload/instaladores.
- [Cierre visual/SE historico](../../reports/NEMESIS_OFFICIAL_VISUAL_REFERENCE_ALIGNMENT_REPORT.md)
  conserva capturas/limites. SHARK y fondo pendientes humanos.
- SE-01: detalle fresco/stale, calendario y Directo en 1366x768/390x844,
  cinco clicks, 0 overflow/errores de consola observados; SIMULATED_QA.
- Esa muestra NO certifica todas las 199 plantillas, todo admin ni iPhone fisico.

## Hogares y preservacion

`templates/`, `static/`, contratos de contexto en app.py/engines. No moverlos,
retirar estilos por nombre Vxxx ni recalcular lifecycle en Jinja/JS.
Topbar, bottom nav, safe area y banner LOCAL SAFE se conservan.
No quitar enlaces/API como si fueran vulnerabilidad sin demostrar permisos rotos.
No reducir tiers reales ni duplicar contexto de cuenta/membresia.

## Deuda clasificada

17 archivos static tracked, 199 templates. Existencia != activos en todas las rutas.
Capas CSS historicas y selectores requieren ownership/render antes de retirada;
no se hereda el numero antiguo de 223 selectores sin medirlo de nuevo.
Los assets de marca pueden compartir contenido o nombre historico sin ser basura.
Un hash igual no autoriza borrar un contrato de ruta o una referencia oficial.

## UX-002: icono de app, 2026-09-09

APP_ICON_IDENTITY = PARTIAL: listo localmente y en PR, no desplegado.
Base c6eaa003e6ae0e9d4af7d98198ec6eefafc97b04; commit selectivo
cdd88e507a9dd422d7e528f8eb795c2030060c3c en codex/app-icon-identity.
[PR #9](https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean/pull/9).

- Maestro: `static/img/app-icons/official_app_icon_master.svg`; reutiliza el
  WebP atmosferico actual intacto, sin generar otro tiburon. No wallpaper.
- Generador offline `tools/build_app_icons.cjs`, sin instalar dependencias;
  una geometria, silueta simplificada a 16/32/48, fondo RGB opaco.
- Normal 16/32/48/64/96/128/152/167/180/192/256/512; ICO 16-256;
  maskable 192/512, escala .80 y alfa del tiburon dentro del circulo seguro.
- Fingerprint `8d0ed4207e73`, reproducible con LF/CRLF. Favicon16 658 bytes,
  favicon32 1739 bytes, PWA512 129358 bytes. No 512 para favicon.
- Manifest mantiene id/start_url/scope `/`, standalone; tema/fondo #020c18.
  Apple Touch 152/167/180, ICO real y metadatos de accesos locales actualizados.
- Rutas de iconos no inicializan negocio; cache HTTP y worker piden version
  nueva. Browser real local confirma activacion y reemplazo de worker previo,
  eliminacion de cache QA, cuatro iconos decodificados, 0 assets rotos.
- QA visual 1366x768/390x844, tamanos 16-512 y formas launcher; navegacion real
  movil Home -> Partidos y desktop Partidos -> Directo, 0 errores JS observados.
  Son representaciones: Windows/iOS/Android/macOS instalados NOT_TESTED.
  Un icono instalado puede exigir aceptar actualizacion o reinstalar segun SO.
- Iconos anteriores: brand.svg sigue ACTIVE para logo/OG, retirado del rol
  favicon/manifest; atmosphere-v2.webp ACTIVE e intacto. official.svg y
  atmosphere.svg LEGACY/REQUIRED_FALLBACK por tests/referencias. No borrados.
  shark-logo.svg ya no existia; 0 referencias de instalacion nuevas a legacy.
- 23 tests propios; 139/139 focales sobre combinacion publicable exacta.
  Suite combinada 602: 590 PASS, 12 LOCAL_SAFE_BLOCKED/NOT_CERTIFIED, 0 errors.
  Performance SHARK existente 10 lecturas: cold 93 ms, hot median 19.1 ms,
  P95 de esta muestra local 23.1 ms; 0 provider calls/render memory writes.
  Compilacion, 199 Jinja, Secret/Privacy del diff y diff-check correctos.
- CI: qa SUCCESS, preflight FAILURE, smoke FAILURE, certify-production SKIPPED.
  Preflight run 34372380601: Browser QA result missing en V944.
  Smoke run 34372380596: No module named playwright durante recoleccion.
  Ambas causas verificadas tambien en logs del SHA base c6eaa003; no son
  fallos inventados por iconos ni justifican eludir checks. CI fix separado.
- No merge/deploy, no Production Sentinel para nuevo SHA; Render workspace
  requiere confirmacion. No cambios de scheduler, CE, DB real ni Sports Truth.

Evidencia privada en `.tmp_reference_review/app_icon_20260909/`:
before.json, verification.json, staged_verification.json, XML, performance.json,
browser_evidence.json y cleanup por run. No publicar esos artefactos ni DB.

## Reconciliacion UX-002 / UX-003 / QA-002

Fecha: 2026-09-09. CREATIVE_DESIGN_DIVISION=PASS_LOCAL (formalizacion e integracion).
APP_ICON_IDENTITY=PARTIAL (implementado, no integrado ni certificado en produccion).
No significa DESIGN_MATCH, lanzamiento comercial ni aprobacion de SHARK/fondo.

### Identidad y contenido demostrado

| Etapa | Evidencia |
|---|---|
| Base preservada / main actual | c6eaa003e6ae0e9d4af7d98198ec6eefafc97b04 |
| App Icon | cdd88e507a9dd422d7e528f8eb795c2030060c3c; padre=base; 22 rutas |
| HEAD y rama remota | 6858aedbbd04211500028b7aaf56c3f5980f833d; padre=App Icon |
| 6858aedb | mensaje `hh`; 35 rutas, SE-01, lectura/contexto/historico deportivo, higiene y documentacion |
| Origen observado | Commit externo a esta ejecucion; GitHub author login bot-NeMeSiS. No identifica por si solo a la persona/proceso que lo creo |
| Relacion | Cadena lineal, base 0 behind / 2 ahead; no cambio a assets, metadata base, generador ni tests de iconos entre cdd88e50 y 6858aedb |
| Main/PR | PR #9 OPEN, merged=false. main permanece en base. El SHA de test-merge de la PR no es un merge efectivo |
| Render actual | NOT_VERIFIED. MCP sin workspace confirmado; runtime publico no accesible por el conector usado |
| Ultima observacion productiva | c6eaa003, DAY 5, 2026-09-08; no es comprobacion nueva |

APP ICON: IMPLEMENTED=YES; COMMITTED=YES; PUSHED_BRANCH=YES;
MERGED_MAIN=NO; DEPLOYED=NOT_VERIFIED (no evidencia); PRODUCTION_CERTIFIED=NO.
PR actual contiene tambien SE/CX: requiere revisar ese contenido antes de merge.
No hubo staging, commit, push, merge, deploy ni ejecucion remota de Actions aqui.

### Division y autoridad

Fuente: [design_contracts.json](../../reference_images/design_contracts.json).
Consumidor: reference_image_manifest_engine -> autonomous_product_qa_engine ->
Founder existente. Sin nuevo engine, endpoint, scheduler o proceso.
CREATIVE_DIRECTOR, BRAND_IDENTITY_DESIGN, PRODUCT_UI_DESIGN, MOBILE_UX_DESIGN,
SPORTS_UX_DESIGN, ADMIN_DATA_UX_DESIGN y VISUAL_REGRESSION_QA son responsabilidades
de Codex y workers ya registrados; no siete empleados autonomos ejecutandose.

Las 16 PNG importadas oficiales se abrieron individualmente. Solo imagenes,
sin payload, instaladores ni codigo de REFERENCE_ONLY. Cada pantalla tiene
proposito, contenido, componentes reales, acciones, responsive, intensidad de marca,
prioridad deportiva, empty state y estado de conformidad. 16 directas + 5 derivadas.
REF-12 muestra Betis-Sevilla y tabs de Match Center, no el portal SHARK.
El manifiesto persistido ya lo reconocia; su generador tenia un override obsoleto,
ahora corregido y protegido por regresion. Ruta canonica /match/<match_id>;
/match/m-1 es el caso sintetico del runner, no una identidad productiva inventada.

FUNCTIONAL_QA y VISUAL_QA conservan estados separados de DESIGN_CONFORMANCE
(campo design_status). Una prueba funcional PASS puede coexistir con rework.
Evidencia ausente=NOT_RUN; evidencia previa necesita revision, captura, viewport
y fingerprint contractual. Automated MATCH no puede aprobar marca. Rechazo humano
prevalece. Estados: DESIGN_MATCH, MINOR_DESIGN_GAP, DESIGN_REWORK_REQUIRED,
FOUNDER_SUBJECTIVE_REVIEW. No se actualizaron baselines ni referencias aprobadas.

Brand kit: ATMOSPHERIC_SHARK, BRAND_SHARK, APP_ICON, WORDMARK, FAVICON,
PWA_ICONS y APPLE_TOUCH_ICON. Iconos/favicons/touch derivan de un solo maestro
tomado del shark atmosferico actual, intacto. Brand Shark vectorial es una fuente
independiente: compatibilidad anatomica conjunta NO certificada. Compartir azul
o tiburon no acredita BRAND_MATCH. Cero wallpapers y cero fondos del SO.

Ocho decisiones duraderas se incorporan a Product Memory existente solo durante
su escritura autorizada: anatomia, oceano, densidad, tipografia, movil, navegacion,
uso de marca y falsos PASS anteriores. Idempotencia probada en almacenamiento QA.
Consultar Founder no escribe esa memoria. Resumen compacto desplegable de siete
areas dentro de Quality existente; contratos detallados bajo disclosure.
Los gaps mostrados vienen del ledger registrado, no de una nueva auditoria global.

### Gates: historico remoto frente a repeticion local

| Gate | Historico GitHub para 6858aedb | Clasificacion / cierre local |
|---|---|---|
| qa | SUCCESS, run 34373698530 | No rerun remoto. Compilacion/Jinja/Sentinel y pruebas locales separadas |
| smoke | FAILURE, run 34373698481, job 102541012212 | CI_ENVIRONMENT_DEFECT: Playwright ausente durante collection. Workflow instala ahora requirements de browser existentes y Chromium antes de pytest; sin filtrar tests |
| preflight | FAILURE, run 34373698511, job 102541011606 | MISSING_REQUIRED_EVIDENCE: browser_qa/V944_MATCH_CENTER_FOUNDATION/browser_qa_result.json. No runner V944 conectado al job que genere las seis capturas requeridas |
| certify-production | SKIPPED | No ejecucion ni certificacion nueva |

Smoke CI fix: 3 lineas, solo workflow; cuatro regresiones (positivo y ausencia de
dependencia/browser/pytest). Segun [Playwright CI oficial](https://playwright.dev/python/docs/ci).
No dependencia nueva de produccion, no continue-on-error, no relajacion de gate.
Instalacion Ubuntu y resultado Actions posteriores: NOT_RUN, cambio aun local.
smoke_check local exit 0; warnings por dos endpoints API historicos ausentes,
no clicks ni integracion productiva certificada por ese check.

V944 reproducido localmente: contratos/Sentinel PASS, unica causa de exit 1 es
Browser QA result missing. No se clasifica como requisito obsoleto sin prueba.
No se copio un JSON historico ni se escribio PASS con seis capturas ficticias.
Para cerrar falta generacion real, aislada, vinculada al candidato en CI; el
navegador Founder de esta tarea NO sustituye la muestra Match Center V944.

Controles posteriores reintentados: V937 lifecycle PASS al reutilizar un directorio
QA heredable (antes WinError 5 por tempfile Windows); producto sin modificar.
V929 PASS tras corregir sys.path del envoltorio local, no su codigo ni expectativas.
V937 client update, V940 Calendar, Match Live Story, Continuous Sentinel static,
release identity y smoke: exit 0. V929 usa tambien matrices guardadas: no anunciar
sus 245 clicks historicos como clicks realizados ahora.
Generadores V915, Master OS, navegacion worker, Secret Guard writer, imports/routes
y link audit: LOCAL_SAFE_BLOCKED al intentar escribir evidencia fuera de QA;
pipeline checker bloqueado por proceso hijo; Madrid audit bloqueo acceso a su DB
fallback y no la abrio. Se conservan logs/limites, no PASS por omision.
V914 opcional no existe y el workflow lo omite por condicion; no es fallo del producto.
Build ZIP de CI no ejecutado localmente: no autorizacion para otro paquete de app.

### Pruebas y preservacion

- Focal Creative/iconos/workforce/Founder/CI: 95/95; regresiones negativas incluidas.
- Focal protegido SE/Sports Truth/Calendar/dashboard/performance: 131/131.
- Suite final: 623 total, 611 PASS, 12 failed XML clasificados LOCAL_SAFE_BLOCKED,
  0 errors, 0 skips. Mismos IDs que la suite previa; resultado global PARCIAL.
- Se conserva SE-01 PASS_LOCAL_SCOPE y su historico 543/555, no se reetiqueta.
- SHARK performance local: 10 lecturas, cold32.9ms, hot mediana18.8ms,
  P95 muestral27.2ms, 0 llamadas externas y 0 escrituras de memoria al render.
  No es latencia/P95 de produccion ni certificacion de toda la app.
- Founder real con sesion y DB sinteticas, desktop1366x768/mobile390x844;
  siete areas, 21 contratos, disclosures y navegacion Panel -> volver. Ocho
  interacciones contando login y back; 0 errores JS/overflow en esta muestra.
- Sin nueva comprobacion de actividad Master/CE; codigo protegido, no asumir ACTIVE.
- No providers, Telegram, Stripe, usuarios reales ni memoria operativa modificados.
- Evidencia, capturas, hashes, compilacion/Jinja/privacidad y resultados exactos:
  `.tmp_reference_review/creative_design_20260909/verification.json`, XML,
  `browser_final.json`, `founder-final-desktop.png`, `founder-final-mobile.png`,
  `performance.json` y `gate_*`. Directorio privado ignorado/excluido del release.
- HEAD/indice y DAY3/4/5 se verifican por hash; no limpieza legacy ni retiros funcionales.
- Verificador final: 4147 archivos previos intactos; 9 existentes modificados
  deliberadamente y 3 nuevos. app.py y assets de icono intactos; 199 Jinja,
  compileall, privacidad/Secret Guard del diff (12 archivos, 0 hallazgos), diff-check PASS.
- Retirada QA por manifiesto tras finalizar procesos: 28 directorios propios
  procesados; 1 temporal V937 retenido por acceso denegado. Se conserva la evidencia
  y no se reparan ACLs ni se llama a esto una limpieza completa. Este limite nuevo
  no reescribe el resultado historico CLEANUP_FINAL_ERRORS=0 de SE-01.

### Decision y siguiente accion

Formalizacion Creative cerrada LOCAL_ONLY. Reconciliacion global PARTIAL: gates
CI y despliegue no cerrados, marca sin aprobacion. Ninguna regresion nueva de
producto demostrada; el cero no es certificacion exhaustiva de produccion.
SAFE_TO_CONTINUE_CX_ORG_01_R2=NO y SAFE_TO_START_RESULTS_01=NO en este cierre.
1. Generar evidencia V944 real en el job aislado y verificar smoke en CI, via PR/checks.
2. Revisar alcance de PR #9 ampliado por 6858aedb antes de cualquier merge.
3. Confirmar workspace Render para leer el despliegue efectivo y certificarlo despues.
No se inicia ninguna de esas fases automaticamente. Gasto nuevo iniciado=0;
facturacion total del sistema no auditada. Secretos expuestos=0.
