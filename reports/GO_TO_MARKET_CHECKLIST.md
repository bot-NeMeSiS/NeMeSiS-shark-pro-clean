# GO TO MARKET CHECKLIST

Fecha Madrid: 2026-07-29  
Estado: Release 1.0 preparation  
Produccion modificada: false

## Executive Summary

- **NeMeSiS puede preparar una beta cerrada inmediatamente.** La base tecnica y de producto esta lista localmente y produccion responde.
- **El lanzamiento comercial abierto requiere cerrar cinco controles.** Pagos, Telegram, cron, persistencia/restore y conversion real.
- **La estrategia recomendada es beta controlada antes de mercado abierto.** Primero probar valor, activacion y confianza; despues abrir publico.

## Checklist De Lanzamiento

| Area | Item | Estado | Evidencia | Owner |
|---|---|---|---|---|
| Producto | Sports Core y centros deportivos PASS | DONE | Checks locales y Browser QA | Producto/CTO |
| Producto | UX local sin fallos bloqueantes | DONE | Browser QA score 100 | Producto/UX |
| Producto | Estados tecnicos traducidos para cliente | OPEN | Experience Platform detecta P2 de copy tecnico | Producto/UX |
| Producto | Track record/metodologia visible | OPEN | No certificado comercialmente | Producto |
| Render | Runtime y health 200 | DONE | Render read-only 200 | DevOps |
| Render | SHA servido coincide con local | DONE | `git_commit_hint` coincide | DevOps |
| Render | Auto deploy validado | OPEN | Runtime indica automatic deploy false | DevOps |
| Cron | Sports cron reciente | PARTIAL | Ultimo tick reciente | Ops |
| Cron | Master tick registrado | OPEN | `NOT_RECORDED` | Ops |
| DB | Persistencia en `/data/database.db` | DONE | Runtime y health | DevOps |
| DB | Backup/restore probado | OPEN | No ejecutado | Ops/Security |
| Telegram | Configurado y protegido | DONE | 403 sin secreto | Ops |
| Telegram | Envio test controlado | OPEN | No ejecutado | Ops |
| Telegram | Dedupe y limites certificados | OPEN | No certificado con envio real | QA/Ops |
| Stripe | Test mode y guardrails | DONE | Runtime mode test, idempotency true | Revenue/CTO |
| Stripe | Checkout test completo | OPEN | No ejecutado | Revenue |
| Stripe | Webhook test completo | OPEN | No ejecutado | Revenue |
| Stripe | Cancelacion/portal certificado | OPEN | Portal ready, flujo no probado | Revenue |
| Legal | Juego responsable visible | PARTIAL | Base de producto, no certificacion legal final | Legal/Producto |
| Legal | Privacidad personalizacion clara | PARTIAL | User Intelligence privacy exists, flujo comercial no certificado | Security |
| Soporte | Canal soporte definido | OPEN | No certificado | Customer Success |
| Soporte | Cancelacion y reembolso claros | OPEN | No certificado | Revenue/Support |
| Observabilidad | Sentinel 10/10 | DONE | 0 issues abiertas | QA/Ops |
| Observabilidad | Alertas humanas | OPEN | No certificado | Ops |
| Comercial | FREE -> PRO -> ELITE medido | OPEN | Sin datos reales de embudo | Revenue |
| Comercial | Beta cerrada definida | OPEN | Plan necesario | CEO/Producto |

## Secuencia Recomendada

1. Cerrar cron/master tick.
2. Certificar restore aislado.
3. Certificar Stripe test completo.
4. Certificar Telegram test controlado.
5. Pulir copy tecnico visible en cliente.
6. Activar beta cerrada con eventos minimos de activacion/conversion.
7. Revisar datos de beta y decidir GO publico.

## Criterio GO Publico

El lanzamiento publico queda autorizado solo cuando:

- Render runtime y SHA siguen alineados.
- Cron completo no esta en PARTIAL.
- Restore aislado pasa.
- Stripe test completo pasa.
- Telegram test controlado pasa.
- Browser QA y Sentinel siguen PASS.
- Primeros usuarios beta entienden el valor antes de 60 segundos.
- FREE -> PRO -> ELITE tiene medicion real, aunque todavia no tenga volumen estadistico.
