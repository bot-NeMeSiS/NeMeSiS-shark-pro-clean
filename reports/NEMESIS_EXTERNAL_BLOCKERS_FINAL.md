# NEMESIS EXTERNAL BLOCKERS FINAL

Fecha Madrid: 2026-08-12

## Criterio

Todo lo que sigue no puede marcarse PASS en este entorno sin acceso, autorizacion o evidencia externa real. No se convierte ausencia de evidencia en PASS.

| Bloqueador | Estado | Que falta | Accion manual requerida | Riesgo | Como certificar |
|---|---|---|---|---|---|
| Render production runtime | EXTERNAL_BLOCKER_RENDER | Deploy/observacion real de servicio | Autorizar push/deploy controlado o acceso read-only | Diferencia local vs Render | Health, SHA, logs, vars, storage y smoke produccion |
| Render Cron Continuous Evolution | EXTERNAL_BLOCKER_RENDER_CRON | Cron `nemesis-continuous-evolution` activo y observado | Configurar runner con SAFE_MODE y storage persistente | No ejecucion autonoma real | 3 ejecuciones en 3 dias naturales, 0 acciones prohibidas |
| Telegram real delivery | EXTERNAL_BLOCKER_REAL_DELIVERY | Un envio tecnico controlado o evidencia real de delivery | Autorizar exactamente 1 mensaje tecnico o revisar delivery logs | Spam/destino incorrecto | getMe, permisos, preview, dedupe, envio unico SENT, logs sanitizados |
| Stripe certification | EXTERNAL_BLOCKER_STRIPE_CERTIFICATION | Checkout/webhook/plan mapping en modo seguro | Autorizar certificacion Stripe test-safe | Cobro real accidental | Test mode, webhook verified, no live charge, membership mapping |
| Production restore | EXTERNAL_BLOCKER_PRODUCTION_RESTORE_CERTIFICATION | Restore aislado con backup real permitido | Facilitar copia/backup autorizado o entorno temporal | Corrupcion de datos si se hace mal | Restore en copia aislada, checksum, manifest, no DB real mutada |
| Production logs/observability | EXTERNAL_BLOCKER_OBSERVABILITY | Logs y metricas Render read-only | Autorizar acceso read-only | Falta de evidencia operacional | Ultimos errores, health, latency, storage, cron logs |
| Real users | EXTERNAL_BLOCKER_REAL_USERS | Trafico/registro/feedback consentido | Abrir beta cerrada | Mezclar QA con negocio real | Primer visitante, registro, FIRST_VALUE, ACTIVATED reales |
| Revenue | EXTERNAL_BLOCKER_REVENUE | Primer intento premium y pago real | Certificar Stripe antes | Cobro sin soporte | Premium intent, checkout test/live controlado, MRR real |

## No bloqueadores locales

- Sports Core, SHARK, centers deportivos, Growth local, Local Safe, Mobile LAN, Continuous Evolution local, Founder Center local y QA local quedan cerrados como PASS LOCAL.
