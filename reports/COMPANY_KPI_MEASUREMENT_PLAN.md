# NeMeSiS SHARK PRO - Plan de medición KPI

## Principios

- Una métrica sin fuente, periodo, población y owner no se publica.
- ROI/win rate usan solo picks cerrados y evaluables; void no es ganado/perdido.
- Índice de Confianza mide calidad/completitud del dato, no probabilidad de acierto.
- Las métricas comerciales proceden de Stripe/ledger reconciliado, no de precios estimados.
- PII se minimiza; dashboards usan agregados.

## KPIs de producto y negocio

| KPI | Definición | Fuente | Existe | Cadencia | Owner | Guardrail |
|---|---|---|---|---|---|---|
| Registrados | Cuentas no eliminadas creadas hasta fin de periodo | users | Sí, no verificado prod | Diario | Product/Data | Excluir test/admin |
| Activos DAU/WAU/MAU | Usuario con evento de valor, no solo pageview | events/audit a definir | Parcial | Diario/semanal | Product | Consentimiento y dedupe |
| Activación | % nuevos que completa calendario/SHARK/favorito/Telegram en 7 días | Funnel eventos | Falta | Semanal | Growth | Cohortes, no acumulado |
| Conversión tier | Usuarios que pasan FREE->PRO/ELITE / elegibles | Stripe+membership | Parcial | Semanal | Commercial | Solo pagos confirmados |
| Churn logo | Cancelados en periodo / activos al inicio | Stripe | Falta certificación | Mensual | Commercial | Distinguir voluntario/involuntario |
| MRR | Ingreso recurrente normalizado de suscripciones activas | Stripe reconciliado | No fiable hoy | Diario/mensual | Finance | Sin estimaciones admin |
| ARPU | Ingreso neto / usuarios de pago activos | Stripe | Falta | Mensual | Finance | Neto de refunds/tax/fees definido |
| CAC | Coste adquisición / clientes nuevos pagados | Ads+finance | Falta | Mensual | Growth | Ventana y atribución explícitas |
| LTV | Margen bruto mensual x vida esperada | Stripe+costes | Falta | Trimestral | Finance | No usar hasta cohortes suficientes |
| Coste/usuario | Render+API+IA+soporte / usuarios activos | Billing+usage | Falta | Mensual | Finance/CTO | Separar fijo/variable |
| Retención D7/D30 | Cohorte activa en día 7/30 | Eventos | Falta | Semanal | Product | Evento de valor definido |
| Tickets/100 usuarios | Casos válidos / activos x100 | Support | Falta | Semanal | Support | Dedupe/reaperturas |

## KPIs deportivos y confianza

| KPI | Definición | Fuente | Existe | Cadencia | Owner | Guardrail |
|---|---|---|---|---|---|---|
| Partidos completos | Registros con ID, equipos, competición, fecha/hora y fuente | matches | Sí | Por sync | Sports Data | Incompletos separados |
| Cobertura | Completos / recibidos elegibles | sync/matches | Parcial | Diario | Sports Data | Por competición/proveedor |
| Frescura | Edad desde timestamp de fuente/último sync válido | cache/sync | Sí parcial | 1-5 min | Realtime | Madrid/UTC trazables |
| Falso live | Live público sin evidencia válida | public arrays + diagnostics | Sí en checks | Continuo | Data Trust | Objetivo 0 |
| Stale público | Registros fuera de ventana visibles | APIs/UI | Sí en checks | Continuo | Data Trust | Objetivo 0 |
| Odds fresh ratio | Cuotas <15 min / cuotas publicables | odds | Parcial | 5 min | Odds | Recorded 15-60 separado |
| Picks publicables | Candidatos completos y vigentes | picks | Sí | Por job | Editorial | Cuota >0 y fresh/recorded permitido |
| Picks publicados | Picks realmente visibles | picks/audit | Sí | Diario | Editorial | Dedupe/canal |
| Win rate | Ganados / (ganados+perdidos) evaluables | track record | Sí | Diario | Data Trust | Muestra y periodo visibles |
| ROI | Beneficio neto / stake evaluable | settlements | Sí | Diario | Data Trust | Void excluido del denominador según política |
| Error de liquidación | Settlements corregidos / cerrados | audit | Falta explícito | Semanal | Data Trust | Objetivo 0; doble revisión |
| Índice de Confianza | Score de completitud/frescura/fuente | trust engine | Parcial | Por dato | Trust | Nunca “probabilidad” |

## KPIs técnicos y operativos

| KPI | Definición | Fuente | Existe | Cadencia | Owner | Objetivo beta |
|---|---|---|---|---|---|---|
| Disponibilidad | Success synthetic / total | Monitor externo | Falta | 1 min | DevOps | >=99.5% |
| Error 5xx | 5xx / requests | Render/APM | Parcial | 1 min | Backend | <0.5%; P0 en auth/payment |
| Latencia p50/p95/p99 | Server response por ruta | APM/synthetic | Puntual | 1 min | Performance | Home <1s; sports <2s p95 |
| MTTA/MTTR | Detect->ack / detect->recover | Incident log | Falta | Por incidente | Ops | P1 MTTA <10m, MTTR <2h |
| Cron success | SUCCESS / ticks esperados | cron ledger | Parcial | Por tick | Automation | >=99% y 0 dobles |
| DB locks | Locks > threshold | DB telemetry | Parcial | 1 min | DB | 0 persistentes |
| Backup age | Ahora - último backup válido off-site | backup ledger | Falta off-site | 15 min | DB/Ops | <RPO |
| Restore success | Drills válidos / planificados | DR log | Falta | Trimestral | DB/Ops | 100% |
| Telegram success | Entregados / intentos válidos | delivery log | Parcial | 5 min | Telegram | >=99%, 0 duplicados |
| Stripe reconcile lag | Pago firmado -> entitlement | webhook ledger | Falta real | 1 min | Payments | <5 min |
| API budget | Uso / cuota | provider metrics | Parcial | 15 min | Data/Finance | alerta 70/85/95% |
| SHARK cost/latency | tokens/coste y p95 por sesión | usage+APM | Parcial | Diario | SHARK/Finance | budget y p95 <2.5s |

## Implementación mínima

1. Diccionario versionado de métricas.
2. IDs de evento y correlation IDs sin PII.
3. Dashboard operativo separado del comercial.
4. Reconciliación diaria Stripe/membership.
5. Export de métricas fuera de SQLite operativa.
6. Quality checks para duplicados, timestamps y denominadores.

## Calidad de dato del KPI

Cada KPI debe mostrar: `source`, `as_of`, `definition_version`, `coverage`, `quality_status` y `owner`. Si falta uno, el estado es “no certificado”, no cero.

