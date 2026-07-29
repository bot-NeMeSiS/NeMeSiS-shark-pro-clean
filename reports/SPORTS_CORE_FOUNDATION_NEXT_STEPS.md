# Sports Core Foundation Next Steps

## Immediate

1. Run full repository QA: py_compile, compileall, full pytest, Jinja, route/link audit, Sentinel, Secret/Privacy Guard and Browser QA.
2. Review Browser QA screenshots for Match Center, Team Center, Competition Center, Live, Calendar, Picks and SHARK.
3. Confirm no runtime route exposes raw provider JSON or debug-only domain internals.

## Current Sports Core State

- Match Center 2.0: PASS local, not production certified in this sprint.
- Sports Knowledge Layer: PASS local.
- Sports Graph Foundation: PASS local.
- Team Center Premium Experience: PASS local.
- Competition Center Premium League Intelligence: PASS local.
- SHARK Intelligence Platform: PASS local; centro trazable sin IA generativa, sin Telegram, sin Stripe y sin llamadas externas.
- User Intelligence Platform: PASS local; privacidad USER-PRIVACY-CONTROLS-V1 y personalizacion preparada sin aplicar Home automaticamente.
- Player Center Premium Sports Identity: PASS local con QA completa; consume Sports Core, Sports Knowledge, Sports Graph, SHARK Intelligence y User Intelligence.
- Sports Intelligence Gateway: PASS local inicial; registra fuentes, evalua compliance, salud y evidencia sin conectar proveedores ni usar scraping.
- Decision Engine: PASS local inicial; organiza evidencia, faltantes, cambios, coincidencias, discrepancias, calidad y confianza sin IA, picks ni predicciones.

## Next Sports Core Sprint

Cerrar Decision Engine con revision Git controlada antes de integrar fuentes reales, Telegram Intelligence, Bankroll u otro modulo visible.

## Team Center Foundation

Use Team Entity and Sports Graph relationships. Do not normalize team names again inside the center.

## Competition Center Foundation

Implemented locally as Competition Center Premium League Intelligence. It consumes Competition Entity, Team Entity, Match Entity, Sports Knowledge and Sports Graph; it does not merge competitions by display name and does not invent standings.

## Player Center Foundation

Implementado localmente como centro de identidad deportiva. Usa Player Entity como partial-first; fotografia, lesion, posicion o dorsal ausentes permanecen como "No disponible" si ninguna fuente real los confirma.

## Future Migration

Move provider adapters toward canonical output gradually while retaining legacy compatibility until consumer scans prove safe removal.

## Human Approval Required

- Any DB schema persistence for canonical entities.
- Any Telegram message generated from the new contract.
- Any provider call added to page render.
- Any removal of legacy adapters.

## SHARK Intelligence Foundation

Implemented locally as SHARK Intelligence Platform. It consumes Sports Core, Sports Knowledge, Sports Graph, Match Intelligence, Team Center and Competition Center. It must not recalculate context, call providers, use generative AI, send Telegram, mutate picks or invent facts.
## User Intelligence Platform

Estado: PASS local pendiente de cierre Git.

La plataforma de inteligencia de usuario queda preparada para entender uso propio de NeMeSiS con consentimiento y control del usuario. Player Center solo prepara la personalizacion futura; no modifica automaticamente la Home.

## Sports Intelligence Gateway

Estado: PASS local pendiente de cierre Git.

El Gateway queda como puerta legal unica para fuentes deportivas futuras. Antes de cualquier uso, una fuente debe estar registrada, revisada por compliance, evaluada en salud y envuelta con procedencia, frescura, evidencia, calidad y limitaciones. No conecta proveedores, no ejecuta scraping, no usa paywalls, no copia articulos ni reutiliza imagenes protegidas.
## Decision Engine

Estado: PASS local pendiente de cierre Git.

Decision Engine queda como motor evidence-first para organizar lo que NeMeSiS sabe, lo que no sabe, la evidencia existente, la evidencia faltante, cambios, coincidencias, discrepancias, calidad y confianza. Consume Sports Core, Sports Knowledge, Sports Graph, Match Intelligence, SHARK, Sports Intelligence Gateway y User Intelligence. No hace IA, no predice, no crea picks, no llama proveedores y no ejecuta acciones automaticas.
## Experience Platform

Estado local: PASS inicial.

La Experience Platform introduce una auditoria read-only de experiencia, consistencia UX, navegacion y densidad visual. No cambia Sports Core, SHARK, APIs, DB, Telegram, Stripe ni produccion. Cualquier pulido visual derivado exige evidencia, aprobacion humana, Browser QA desktop/tablet/mobile y Sentinel limpio.
## Action Platform

Estado local: PASS inicial pendiente de QA final.

Action Platform convierte la arquitectura existente en una experiencia personal: Smart Home, favoritos inteligentes, watchlist, alertas, briefing, recap, actividad e historial de decision. No crea motor nuevo. No decide por el usuario. No genera picks, predicciones, Telegram ni pagos. Cada bloque conserva procedencia, evidencia, frescura, calidad y limitaciones.

## Product Finalization Release Candidate

- Estado local: finalizacion de producto ejecutada sobre cliente, admin, desktop, tablet y movil, sin deploy.
- Contrato: `NEMESIS-PRODUCT-FINALIZATION-RELEASE-CANDIDATE-V1`.
- Evidencia: Browser QA local read-only sobre 24 superficies x 3 viewports, score de experiencia 100/100, 0 fallos, 0 llamadas externas, 0 Telegram, 0 Stripe y 0 escrituras DB reales.
- Cambios permitidos: pulido de copy visible, accesibilidad, targets tactiles, densidad visual y auditoria.
- Guardrails: no cambia Sports Core, SHARK, Gateway, datos deportivos, pagos, Telegram ni produccion.
- Produccion: no certificada; no hubo push ni deploy.
