# NeMeSiS SHARK PRO - Plan 30/60/90 días

## Inmediato: 0-7 días

| Pri. | Acción | Owner | Esfuerzo | Riesgo/dependencia | Beneficio | Criterio y prueba | Rollback | Nueva versión |
|---|---|---|---|---|---|---|---|---|
| P0 | Clasificar PII/patrones sensibles del repo público | Security/Privacy | M | Acceso admin GitHub/legal | Cierra exposición potencial | Inventario 100%, scan limpio, rotación si aplica | Restaurar solo artefacto no sensible | No, operación de seguridad autorizada |
| P0 | Backup cifrado off-site + restore aislado | DB/Ops | M | Almacenamiento/llaves | Reduce pérdida catastrófica | Integrity, RPO/RTO medidos, auth y counts | Safety snapshot | Puede requerir hotfix controlado |
| P1 | Reparar Secret Guard sin desactivarlo | Security/CI | S | Motor oficial existente | Gate fiable | Canary bloquea, limpio pasa | Revert del wrapper | No cambio de producto |
| P1 | Cerrar webhook Telegram y secret por URL | Security/Telegram | M | Compatibilidad cron | Evita abuso/filtración | No auth 403, header pasa, dry-run | Ventana de deprecación | Hotfix V937 autorizado, no nueva versión |
| P1 | Endurecer cookie y runtime público | Backend/Security | S | HTTPS/SSO | Protege sesión/internals | Headers Render y auth smoke | Revert config | Hotfix |
| P1 | Certificar producción read-only | DevOps/QA | S | Acceso Render | Verdad operativa actual | SHA/runtime/5xx/DB/freshness 60 min | Ninguno | No |
| P1 | Certificar Stripe sin cobro | Payments | M | Credenciales/test dashboard | Evita membresías incorrectas | Catálogo/webhook/portal test y reconcile | Desactivar checkout | Config/hotfix solo si falla |
| P1 | Revisión legal y privacidad | Dirección/Legal | M | Asesoría y datos empresa | Permite beta responsable | Textos/owner/jurisdicción aprobados | Mantener beta cerrada | Contenido legal |
| P1 | Definir operador alternativo y break-glass | Dirección/Ops | S | Segunda persona | Reduce bus factor | Simulacro read-only | Revocar acceso | No |
| P1 | Congelar ELITE+ y unificar catálogo/precios | Product/Payments | S | Decisión comercial | Elimina promesa ambigua | UI/admin/Stripe misma fuente | Volver a mostrar solo tras implementación | Config/copy |

## Corto plazo: 8-30 días

| Pri. | Acción | Owner | Esfuerzo | Riesgo/dependencia | Beneficio | Criterio y prueba | Rollback | Nueva versión |
|---|---|---|---|---|---|---|---|---|
| P1 | Monitor externo runtime/SHA/5xx/frescura | DevOps/Ops | M | Proveedor monitor | Detección <2 min | Alert test y runbook | Desactivar integración | No necesariamente |
| P1 | Cron ledger y dead-man por job | Automation | M | Correlation IDs | Demuestra ejecución | Dos ciclos y alerta missed tick | Feature flag | Hotfix menor |
| P1 | Certificación Telegram con allowlist | Telegram/QA | M | Destino de prueba | Confirma entrega/dedupe | Dry-run + un test autorizado | Kill switch | No nueva función |
| P1 | Reauth/doble control para restore | DB/Security | M | Flujo admin | Reduce error catastrófico | Denial/approval/restore drill | Mantener restore deshabilitado | Hotfix |
| P2 | Cerrar Data Vault connection leak | Backend/DB | S | Test Windows/Linux | Menos locks | 100 ciclos limpios | Revert | Hotfix |
| P2 | Resolver ruta duplicada y tests obsoletos | Backend/QA | S | Navegación | CI fiable | Una regla, suite verde | Alias explícito | Hotfix |
| P2 | Entorno de test hermético Python 3.11.9 | CI/Architecture | M | Lock deps | Reproducibilidad | Clean install + pytest offline/cache | Requirements anterior | No |
| P2 | Profiling Calendar/Live/Picks | Performance | M | Telemetría prod | p95 <2 s | 30 mediciones/route, no provider render | Revert cache/query | Hotfix si cambia código |
| P2 | DSAR export/delete runbook | Privacy/Support | M | Retención legal | Cumplimiento | Solicitud ficticia aislada | Cancelar antes de ejecución | Puede requerir feature |
| P2 | SLA soporte y estado externo | Support/Ops | S | Canal independiente | Confianza | Plantillas y simulacro | N/A | No |

## Medio plazo: 31-60 días

| Pri. | Acción | Owner | Esfuerzo | Riesgo/dependencia | Beneficio | Criterio y prueba | Rollback | Nueva versión |
|---|---|---|---|---|---|---|---|---|
| P2 | Extraer dominios del monolito incrementalmente | Architecture | L | Test coverage | Menor blast radius | Rutas iguales, módulos sports/auth/payments | Revert por módulo | Sí, planificada |
| P2 | Prueba de carga y umbral Postgres | DB/Performance | M | Datos anonimizados | Decisión de escala | 2x carga beta con SLO | Volver al baseline | No para prueba |
| P2 | Pipeline de métricas/KPI | Data/Product | L | Event taxonomy | Aprendizaje real | Dashboard con quality metadata | Feature flag | Sí |
| P2 | Retención/rotación de logs | Ops/Privacy | M | Legal | Menos presión/PII | Política aplicada y restore de auditoría | Restaurar archive | Hotfix/config |
| P2 | Contract tests proveedores | Data/QA | M | Sandboxes | Menos roturas por API | Fixtures/version drift alert | Pin versión | No |
| P2 | Cohorte beta gratuita 20-50 | Product/Support | L | P0/P1 cerrados | Evidencia de valor | D7/D30, feedback, incidentes | Cerrar invitaciones | No |
| P2 | Accesibilidad con usuarios/teclado | UX/QA | M | Beta | Inclusión/calidad | WCAG AA en flujos críticos | Revert CSS puntual | Hotfix |

## Largo plazo: 61-90 días

| Pri. | Acción | Owner | Esfuerzo | Riesgo/dependencia | Beneficio | Criterio y prueba | Rollback | Nueva versión |
|---|---|---|---|---|---|---|---|---|
| P2 | DR regional/proveedor alternativo | CTO/DevOps | L | Coste/arquitectura | Continuidad | Simulacro documentado dentro de RTO | Mantener Render primario | Sí/infra |
| P2 | Migración Postgres/cola si umbral se supera | Architecture/DB | L | Datos/migración | Escala y concurrencia | Dual-read/reconcile, rollback probado | SQLite read-only snapshot | Sí |
| P2 | Automatizar reconciliación Stripe | Payments | M | Webhook certificado | Menos tickets | Drift detectado <5 min | Modo manual | Sí |
| P2 | Economía unitaria y pricing | Finance/Product | M | Datos beta | Margen sostenible | CAC/LTV/coste por tier | Mantener precios | Config/comercial |
| P2 | Equipo mínimo y guardia | Dirección | L | Presupuesto | Menor bus factor | On-call y sustitución simulada | N/A | No |
| P3 | Limpieza repo histórica | Release/Security | L | Clasificación/backup | Clones/CI rápidos | Sin runtime/test/evidencia perdida | Rama/tag archive | No |
| P3 | Beta de pago limitada | Dirección | L | Todos gates | Validar negocio | 0 P0/P1, soporte y refund policy | Pausar checkout | No nueva función |

## Secuencia de decisión

No avanzar a beta de pago hasta completar: privacidad -> backup/restore -> seguridad endpoints -> producción -> pagos/Telegram -> legal -> soporte -> beta gratuita.

