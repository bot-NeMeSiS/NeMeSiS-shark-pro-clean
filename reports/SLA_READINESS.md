# SLA READINESS

Fecha Madrid: 2026-07-29

Alcance: evaluar si NeMeSiS puede prometer niveles de servicio.

Produccion modificada: false

Commit/push/deploy: no ejecutados

## Executive Summary

- **NeMeSiS no debe prometer todavia un SLA comercial fuerte.** La evidencia local y algunos informes previos muestran buena salud, pero faltan alertas externas, backup/restore certificado, soporte medido y pruebas de carga.
- **Para beta, es viable declarar objetivos internos de servicio, no garantias contractuales.** Se puede operar con SLO internos y comunicacion honesta: "servicio en beta controlada, soporte manual, sin garantia de disponibilidad comercial".
- **El SLA real requiere observabilidad independiente.** Un panel interno no sustituye monitores externos, alertas a humanos y evidencia de respuesta.

## Estado Por Capacidad

| Capacidad | Estado | Evidencia | Falta |
| --- | --- | --- | --- |
| Health endpoint | PASS_LOCAL | `/api/health` declarado y usado | Monitor externo recurrente. |
| Runtime/SHA | PASS_LOCAL | `/api/runtime-version` existe | Certificacion tras deploy. |
| Error tracking | PARTIAL | Observability/Sentinel local | Agregacion y alertas externas. |
| Uptime | NOT_CERTIFIED | No hay historico SLA | Monitor 30 dias. |
| Latencia | PARTIAL | Browser QA local | p95 real por ruta. |
| Backups | PARTIAL | Funciones y reportes | Restore drill y offsite. |
| Soporte | NOT_CERTIFIED | Runbooks | SLA humano y canal real. |
| Pagos | PARTIAL | Stripe test ready | Flujo test completo. |
| Telegram | PARTIAL | Proteccion/dry-run | Entrega controlada. |

## SLO Internos Recomendados

| Servicio | SLO beta | SLO publico futuro |
| --- | ---: | ---: |
| Uptime web | 99.0% mensual | 99.5%-99.9% mensual |
| Health 5xx | <0.5% | <0.1% |
| p95 rutas criticas | <3s | <2s |
| Runtime/health p95 | <1s | <500ms |
| Cron sports freshness | <30 min en horario activo | <15 min si live/picks dependen de ello |
| Telegram dedupe | 100% sin duplicados conocidos | 100% |
| Stripe webhook ack | 99% test | 99.9% real |
| Restore RTO | <8h beta | <2h publico |
| Soporte P1 | <4h beta | <1h publico |

## No Prometer Todavia

- Disponibilidad 99.9%.
- Respuesta soporte 24/7.
- Datos deportivos en tiempo real garantizados.
- Picks garantizados.
- Telegram sin fallos.
- Activacion instantanea de pagos sin webhook test completo.
- Restore en minutos sin prueba real.

## Requisitos Antes De SLA Publico

1. Monitor externo de uptime y endpoints criticos.
2. Alertas a humano por P0/P1.
3. Registro de incidentes.
4. Restore drill medido.
5. Prueba de carga.
6. Stripe test completo.
7. Telegram test controlado.
8. Politica de soporte y cancelacion visible.
9. Error budget mensual.
10. Informe semanal de SLO.

## Politica De Comunicacion

### Beta

"NeMeSiS esta en beta controlada. Monitorizamos disponibilidad, datos y pagos; algunas funciones pueden degradarse. No garantizamos datos en tiempo real ni resultados deportivos. Los picks y analisis son informativos y responsables."

### Publico futuro

"NeMeSiS opera con objetivos de disponibilidad, soporte y recuperacion publicados. Cualquier incidencia relevante se comunicara con estado, impacto y tiempo estimado."

## Decision

SLA READINESS: PARTIAL

SLO INTERNOS: READY_FOR_BETA

SLA COMERCIAL PUBLICO: NOT_READY

## Siguiente Unica Accion

Definir y medir durante 14 dias los SLO internos beta: uptime, p95, 5xx, cron freshness, Stripe test, Telegram dry-run y soporte.
