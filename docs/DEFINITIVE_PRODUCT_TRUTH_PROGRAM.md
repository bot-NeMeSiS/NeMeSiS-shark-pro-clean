# NeMeSiS Definitive Product Finish & Truth Integration

## Control único — 4 octubre 2026

Rama maestra: `integration/definitive-product-truth-20261004`. Base real main/LIVE: `b7e8aea16e7b0b0cd995d2ed706eb44ca9e73506` (#196). Este documento sustituye planes paralelos para este programa; las PR fuente conservan historial. NO MERGE / NO DEPLOY. No fases 4–11. No cambios en secretos, usuarios, datos reales, pagos ni Telegram/proveedores reales.

## Inventario y decisión de integración

| Frente | Evidencia real | Decisión |
|---|---|---|
| Operaciones, backup, Cron | main #196; Render web y Cron LIVE en b7e8aea1 | Reutilizado desde main. No repetir hotfix. Certificación pendiente |
| Sports Truth | PR DRAFT #187, head remoto 31d563d307a1d5d6d4c2d956b95fe346c0fd8696, mergeable=false | Contrato de referencia obligatorio. Código permanece separado mientras gate abierto; resolver conflictos en candidato aislado y revalidar antes de incorporar |
| TV automática | PR DRAFT #194, head 68bb4fe85282e9c3b4e13b45caa83d2ec3894f9f | Absorbida con merge local en rama maestra; se conserva su historial. Un solo engine SportsDB y Sports History |
| Visual alternativo | PR DRAFT #195, head 0e24b85e0fdd155edd075cb85fc815e3b330f803 | No incorporar otra stylesheet premium. Recuperar mejoras útiles en los estilos consolidados tras comparar con rediseño activo |
| Core visual activo | Rama redesign/core-client-founder-20261004, chat «Rediseña NeMeSiS SHARK PRO» | Propietario del bloque A y sistema visual. Cambios sin commit en checkout principal: no copiar ni editar simultáneamente. Absorber commit revisado cuando entregue QA |
| TV parcial local anterior | feature/automatic-broadcast-client-20261004, copia nemesis-tv | No absorber: trabajo incompleto, escritura fallida documentada y proveedor equivalente en #194 |
| Cliente, media, postmatch, automatización, Founder previos | Múltiples ramas/worktrees locales y cambios ya absorbidos por main | Comparar ancestros y diferencias con main antes de rescatar cualquier commit. Existencia de rama no implica trabajo pendiente |

PR fuente: https://github.com/bot-NeMeSiS/NeMeSiS-shark-pro-clean/pull/187, /194, /195. No cerrar automáticamente las PR fuente ni reescribir ramas ajenas. La rama maestra es el destino de integración; las fuentes no son nuevos programas independientes.

## Bloques, dependencias y aceptación

| Bloque | Resultado | Dependencias y salida |
|---|---|---|
| A | Shell, Home, navegación Sports First → SHARK Second → Betting Third | Reutilizar rediseño activo. Dark Premium; Broadcast deporte; SHARK verde/violeta; rojo LIVE/alerta real. Consolidar CSS existente y bundle generado. PC/tablet/móvil antes/después, rutas y navegación cliente/admin separados |
| B | Live, Calendar, Match Center, TV | A + contrato #187. #194 ya absorbida; extender lecturas persistidas en lotes a Home/Calendar/Live, cero I/O proveedor al render. No mostrar evidencia caducada como confirmación actual |
| C | Picks, Combinadas, SHARK | A/B; mismo match canónico y clocks. Cuotas caducadas no utilizables; riesgo y membership claros; no cambiar lógica editorial ni cobros |
| D | Cuenta, membresías, login, onboarding, Telegram cliente, favoritos, estados | A; inventariar todas las rutas cliente y aliases. Lenguaje natural, sin diagnósticos de runtime/proveedor; ausencia real diferenciada de error |
| E | Founder/Admin | A; misma identidad, navegación y lenguaje propios. Alertas accionables arriba, telemetría abajo, sin secretos ni acciones peligrosas como CTA principal; móvil usable |
| F | Móvil, rendimiento y QA final | A–E; comparación contra misma base/datos. Jinja, assets/logos/fallbacks, overflow, rutas, console/JS/5xx, Madrid Time, Truth/Cron/Telegram aislado y queries/external calls |

El trabajo puede avanzar antes del gate; la producción no. Cada bloque sólo se marca terminado con evidencia de su SHA exacto. Si falta tablet, sesión autenticada, métricas o capturas, registrar pendiente; nunca inferir PASS.

## Gate de producción — sigue BLOQUEADO

Render confirmado: workspace tea-d7mec77lk1mc73bjf9bg; web srv-d7t9j2favr4c738hm0i0; Cron crn-d8mlmhq8qa3s73e9v2tg. Disco montado /data, tamaño configurado 2 GB. Web y Cron LIVE en b7e8aea1. Autodeploy existente apunta a main; no se ha modificado y no se publica main.

Muestra observada: 15 ticks 20:05–21:15 Madrid, 4 octubre, overall PARTIAL, HTTP sports/odds/Telegram 200, backup_created=false y SKIPPED_NOT_DUE. Esto acredita actividad, NO certificación global ni un backup nuevo. Hay limitaciones de acceso API-Football y fallback SportsDB; no inventar cobertura.

Para certificar: comprobar al menos 12 ticks consecutivos sin fallos de ejecución y revisar resultados por lane; observar ventana nocturna; backup automático real de la ventana 04:30–06:30 Madrid del 5 octubre con archivo, manifiesto, hash, integridad y restore aislado. Verificar capacidad libre real y retención del disco; el tamaño configurado no acredita espacio disponible. Comprobar CI Linux/QA del HEAD tras actualizar contra main y resolver #187. Certificación completa se comunica, pero NO autoriza merge/deploy o fases posteriores por sí sola.

## QA, métricas y riesgos

La evidencia de #187 es histórica de otra base/HEAD: 338 tests relevantes y 16 capturas declaradas, con 26 fallos reproducidos en base. Su descripción menciona 2fd70268, pero el head remoto es 31d563d3: no trasladar aquella certificación a este HEAD.

Benchmark anterior #187, sintético: Home 51.22→70.81 ms; Calendar 93.77→101.06; Live 68.68→81.49; Match Center 64.74→93.07; SHARK 77.69→113.59. +1 consulta por ruta, +2 SHARK. Es coste de provenance, no mejora ni latencia Render. Medir de nuevo tras integración.

Riesgos: #187 conflictiva y desactualizada; #195 acumula CSS; TV necesita política de frescura de lectura y expansión a superficies; rediseño activo sin commit; sólo ~45 MB libres en C: al inspeccionar. Usar checkout parcial para integrar sin copiar datos/runtime. No ejecutar la app contra producción ni crear datos deportivos ficticios para capturas de producto.

Siguiente paso exacto: recoger el commit y QA del bloque A del rediseño activo, compararlo con #195, integrar sólo estilos consolidados y repetir QA del candidato maestro. Después ampliar B mediante lectura por lotes de la misma memoria TV; resolver #187 en candidato aislado sin desplegar. Mantener todos los gates y registrar resultados por SHA.
