# LAUNCH RISK MATRIX

Fecha Madrid: 2026-07-29  
Alcance: Release 1.0 commercial readiness  
Produccion modificada: false

## Executive Summary

- **No hay un P0 confirmado en la auditoria actual.** Produccion responde, no hay errores activos y no se detectaron secretos.
- **Hay P1 operativos y comerciales que bloquean lanzamiento publico.** Cron parcial, pagos no certificados, Telegram no enviado en test, soporte/cancelacion no certificados y conversion no medida.
- **El riesgo mas peligroso no es tecnico, es de confianza comercial.** Si el usuario paga antes de entender valor, soporte y limites, el producto puede recibir rechazo aunque la arquitectura sea buena.

## Matriz De Riesgos

| ID | Riesgo | Categoria | Probabilidad | Impacto | Severidad | Evidencia | Mitigacion |
|---|---|---|---|---|---|---|---|
| R1 | Cron queda en PARTIAL | Operacion | Media | Alto | P1 | `v937_sports_cron_status=PARTIAL` | Diagnosticar master tick y registrar estado real |
| R2 | Master tick no registrado | Observabilidad | Media | Alto | P1 | `v937_cron_master_status=NOT_RECORDED` | Cerrar observabilidad cron antes de GO |
| R3 | Stripe checkout falla en cliente real | Ingresos | Media | Alto | P1 | Flujo test completo no ejecutado | Certificar checkout/webhook/cancelacion en test |
| R4 | Telegram envia mal o duplica | Reputacion | Media | Alto | P1 | Envio real no ejecutado en este sprint | Test controlado con canal seguro |
| R5 | Restore no funciona | Continuidad | Baja-Media | Muy alto | P1 | Restore no certificado | Drill aislado de backup/restore |
| R6 | Usuario no entiende por que pagar | Comercial | Alta | Alto | P1 | Conversion no medida | Beta cerrada + onboarding + preview premium |
| R7 | Estados tecnicos visibles rompen confianza | UX | Media | Medio | P2 | Experience Platform P2 copy tecnico | Copy audit cliente/admin |
| R8 | Stale odds generan mala decision | Datos | Media | Alto | P1 | `v935_stale_odds=6` | Criterio de bloqueo/explicacion de odds stale |
| R9 | Auto deploy no esta certificado | DevOps | Media | Medio | P2 | `v939_automatic_deploy=false` | Definir flujo release manual/automatico |
| R10 | Soporte insuficiente tras pago | Customer Success | Alta | Alto | P1 | Soporte no certificado | Canal, SLA y cancelacion visibles |
| R11 | Privacidad de personalizacion no se entiende | Legal/Confianza | Media | Medio | P2 | User Intelligence existe, flujo no medido | Centro de privacidad visible |
| R12 | Beta sin medicion no aprende | Producto | Alta | Medio | P2 | No hay funnel real | Eventos minimos y dashboard beta |
| R13 | Promesa de picks percibida como garantia | Legal/Reputacion | Media | Alto | P1 | Track record/metodologia no certificado | Copy responsable y resultados reales |
| R14 | Produccion se degrada bajo trafico | Rendimiento | Baja-Media | Alto | P2 | No hay carga real | Smoke + medicion rutas criticas |
| R15 | Admin depende de una persona | Operacion | Media | Alto | P2 | Runbooks humanos no certificados | SOP de incidencias y backups |

## Riesgos Por Gate

| Gate | Riesgo dominante | Estado |
|---|---|---|
| Render | Auto deploy no certificado | P2 |
| Telegram | Entrega real no certificada | P1 |
| Stripe | Flujo comercial no certificado | P1 |
| Persistencia | Restore no probado | P1 |
| UX | Copy tecnico visible | P2 |
| Conversion | Sin datos de embudo | P1 |
| Soporte | Sin proceso visible | P1 |
| Observabilidad | Cron parcial/master tick | P1 |

## Decision

Launch Risk: MEDIUM-HIGH para lanzamiento publico.  
Launch Risk: MEDIUM para beta cerrada con usuarios limitados y pagos controlados/test.

## Riesgo Residual Aceptable Para Beta

Se acepta beta si:

- No se cobran pagos reales sin Stripe test certificado.
- Telegram se prueba solo en canal controlado.
- Se comunica que es beta.
- Se mide activacion y errores.
- Existe plan de rollback y soporte manual.
