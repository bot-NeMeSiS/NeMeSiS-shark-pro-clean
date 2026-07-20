# NeMeSiS SHARK PRO - Observabilidad y alertas

## Diagnóstico

NeMeSiS tiene muchas comprobaciones internas, pero aún no una cadena completa “detectar -> avisar -> responder”. La mayoría registra, genera reportes o se ejecuta manualmente. Un score Sentinel 10/10 no demuestra disponibilidad de producción ni ausencia de riesgos fuera de su conjunto de reglas.

## Sistemas actuales

| Sistema | Detecta | No detecta/cobertura débil | Cadencia/entorno | Avisa/corrige | Evidencia | Falta |
|---|---|---|---|---|---|---|
| Continuous Sentinel | Rutas, patrones, issues conocidos | PII, Secret Guard roto, DR, proveedor real | Manual/local y panel | Registra; autopilot limitado | 10.0, 39 diagnósticos | Heartbeat externo y tests de cobertura |
| Sentinel AutoPilot | Incidencias deduplicadas | No debe remediar destructivo | Código/admin | Puede proponer | Histórica | Política explícita y kill switch |
| `/api/health` | App/DB básica | Dependencias profundas, SHA | On request | Solo responde | 200 local temporal | Synthetic cada minuto |
| Runtime version | Versión/archivos/alignment | Commit SHA real si no se expone de forma segura | Público | Solo responde | Local | SHA allowlisted y monitor diff |
| Route smoke | 404/500/redirects | Flujos JS y efectos | CI/local | Bloquea release | 26-58 rutas según check | Synthetic crítico producción |
| GitHub Actions | Compile/checks/smoke | Producción real, datos frescos | Push/PR | Bloquea PR | Estado remoto divergente | Entorno hermético y Secret Guard |
| Render logs | Start/5xx/jobs | UX y negocio si no se consultan | Producción | Registra | No accesibles aquí | Export/alertas y retención |
| Cron health | Last/next/result parcial | Todos los jobs reales | Admin/DB | Registra | Solo sports cron blueprint | Dead-man switch por job |
| Telegram delivery logs | Enviado/fallido/dedupe | Experiencia real si no alertan | DB/admin | Retry parcial | Dry-run histórico | Alertas, allowlist, SLO |
| Stripe webhook logs | Event/firma/idempotencia | Dashboard Stripe externo | Evento | Retry Stripe | Código local | Reconciliation y alertas 4xx/5xx |
| DB health | Acceso/integridad puntual | Crecimiento, locks y disco continuo | Local/on demand | Retry | Temp/local | Métricas size/lock/latency/off-site |
| API usage guard | Quota/status parcial | Facturación total multi-provider | Sync/admin | Backoff | Código | Budget central y forecast |
| Data freshness | Stale/live/odds | Alimentación real si cron muere sin alerta | Render/UI/checks | Excluye | Checks V937 | SLO + alertas externas |
| Browser QA | Overflow/layout/status | Interacción real, accesibilidad completa | Manual | Reporta | 238 capturas | Release visual gate reducido |
| Mobile QA | 390 y otros perfiles históricos | Dispositivos reales/teclado/red | Manual | Reporta | Capturas | Device lab mínimo |
| Secret Guard | Secretos tracked | PII y runtime secrets | Debería ser CI | Bloquea | **Roto** | Restaurar de inmediato |
| Navigation Integrity | Rutas/enlaces/loops | Ruta duplicada exacta y JS complejo | CI/local | Reporta | 929 enlaces | Duplicate route gate y click E2E |
| Version/SHA alignment | Archivos de release | Render SHA si no integrado | Release/runtime | Reporta | Local | Monitor main vs Render |
| Backups | Archivo/hash | Restore real/off-site/integridad completa | On demand | Crea/retiene | Temp; connection leak | Restore drill y backup age alert |

## SLO recomendados

| Servicio | SLI | Objetivo inicial beta | Alerta |
|---|---|---:|---|
| Web | Disponibilidad rutas críticas | 99.5% mensual | 2 fallos/2 min |
| Home | p95 servidor | <1.0 s | >1.5 s 5 min |
| Dashboard | p95 | <1.5 s | >2.0 s 5 min |
| Calendar/Live/Picks | p95 | <2.0 s | >3.0 s 5 min |
| SHARK seguro | mediana/p95 | <1.5/<2.5 s | p95 >3 s |
| Sports sync | edad último SUCCESS | <30 min | >30 min warning, >60 critical |
| Live | edad de evidencia | <120 s | cualquier stale público P0/P1 |
| Odds | fresh/recorded/stale | <15/<60/>60 min | stale público inmediato |
| Cron | heartbeat | 2x intervalo | missing tick |
| Telegram | success/dedupe | >99%, 0 duplicados | 3 fallos o 1 duplicado |
| Stripe webhook | 2xx/reconcile | >99.9%, <5 min | cualquier pago no reconciliado |
| DB | lock/error/integrity | 0 persistentes | lock >30 s, integrity fail P0 |

## Alertas mínimas

1. Runtime/SHA de Render distinto de `main`.
2. 5xx o 502 en rutas críticas.
3. DB mount/path/integrity/size/lock.
4. Sports sync stale y proveedor quota.
5. Falso live/stale/odds inválida pública.
6. Cron sin tick o duplicado.
7. Telegram fail/duplicate/wrong allowlist.
8. Stripe webhook 4xx/5xx o unreconciled.
9. Secret/PII scanner.
10. Backup age/restore drill overdue.

## Canales

- P0/P1: canal operativo fuera de la app + llamada/SMS/pager.
- P2: admin y digest operativo.
- P3/P4: backlog semanal.
- Nunca alertar al mismo Telegram que se está monitorizando como único canal.

## Datos de evento

Cada métrica debe incluir entorno, versión, SHA, ruta/job, resultado, duración y correlation ID. IDs de usuario, payloads y secretos deben redactarse o tokenizarse.

## Prioridad

Implementar primero un synthetic monitor externo read-only para runtime/SHA, home, login, health y frescura. Sin él la empresa puede estar degradada mientras sus checks internos siguen verdes.

