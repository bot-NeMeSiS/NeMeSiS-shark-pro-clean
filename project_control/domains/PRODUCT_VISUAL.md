# Product / Visual

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
