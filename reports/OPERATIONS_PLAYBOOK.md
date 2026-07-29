# OPERATIONS PLAYBOOK

Fecha Madrid: 2026-07-29

Objetivo: sistema operativo para operar NeMeSiS sin depender de memoria personal.

Produccion modificada: false

Commit/push/deploy: no ejecutados

## Executive Summary

- **NeMeSiS necesita operar como una empresa, no como una carpeta con mucho codigo.** La plataforma ya tiene Developer Center, Company Board, Operations Center, Sentinel y QA. El siguiente salto es ritual operativo: quien mira que, cuando, con que criterio y que decision toma.
- **El playbook debe priorizar estabilidad, evidencia y control humano.** Automatizar checks es seguro; automatizar pagos, Telegram real, restores o deploys sin aprobacion no lo es.
- **El objetivo operativo minimo es que un segundo operador pueda mantener beta durante una semana sin Damian.** Si eso no es posible, la empresa aun no esta lista para escalar.

## Roles Operativos

| Rol | Responsable actual | Responsabilidad profesional |
| --- | --- | --- |
| CEO/Owner | Damian | GO/NO-GO, riesgo comercial, comunicacion critica. |
| CTO | Damian/Codex | Arquitectura, escalabilidad, deuda tecnica, seguridad. |
| Ops Lead | Damian/Codex | Health, cron, Render, backups, incidentes. |
| QA Lead | Codex asistido por Damian | Browser QA, Sentinel, routes, regression gates. |
| Security Lead | Damian/Codex | Secret Guard, Privacy Guard, permisos, logs. |
| Support Lead | Pendiente | Usuarios, pagos, cancelaciones, incidencias. |
| Data Lead | Pendiente | Frescura deportiva, fuentes, licencias, calidad. |

## Rutina Diaria

| Momento | Revision | Decision |
| --- | --- | --- |
| Inicio del dia | `/api/health`, `/api/runtime-version`, Operations Center | PASS/PARTIAL/BLOCKED. |
| Antes de cron fuerte | Ultimo tick, next tick, data freshness, stale | Si PARTIAL, no enviar Telegram masivo. |
| Antes de pagos | Stripe mode, webhook, idempotency, soporte disponible | Si no certificado, solo test. |
| Antes de Telegram | Queue, dedupe, destino, limites, dry-run | Si no hay evidencia, no enviar. |
| Fin del dia | Sentinel, errores, 5xx, backup age, tickets | Abrir tareas P1/P2. |

## Rutina Semanal

1. Ejecutar QA local completa.
2. Revisar Sentinel y AutoPilot.
3. Revisar Route/link audit.
4. Revisar Privacy/Secret Guard.
5. Verificar backup y checksum.
6. Ejecutar restore drill aislado al menos en ciclo de release.
7. Revisar coste/uso de APIs.
8. Revisar conversion, activacion y soporte si hay beta.
9. Cerrar o re-priorizar riesgos P1.

## Flujo De Cambio Seguro

1. Definir alcance.
2. Confirmar rama y estado Git.
3. Crear backup del diff si hay cambios locales.
4. Implementar minimo necesario.
5. Ejecutar QA afectada.
6. Ejecutar Sentinel/Privacy/Secret Guard.
7. Documentar evidencia.
8. Commit local unico por sprint.
9. Solicitar autorizacion de push/deploy.
10. Certificar Render read-only.
11. Mantener rollback documentado.

## Flujo De Release

| Gate | Criterio |
| --- | --- |
| Git | main limpio, commits claros, origin alineado. |
| Build | py_compile, compileall, pytest, checks especificos. |
| Security | Secret Guard y Privacy Guard PASS. |
| UX | Browser QA desktop/tablet/mobile PASS. |
| Routes | route/link audit PASS. |
| Runtime | `/api/runtime-version` alineado tras deploy. |
| DB | health y backup actual. |
| Cron | ultimo/proximo tick registrado. |
| Telegram | dry-run y envio controlado si aplica. |
| Stripe | test checkout/webhook si aplica. |
| Rollback | SHA y backup disponibles. |

## Operacion De Datos Deportivos

- Nunca llamar proveedores caros desde render de pagina.
- Mantener cache y snapshots.
- Bloquear uso comercial de fuentes no registradas en Gateway.
- Marcar datos stale de forma visible.
- No mostrar falsos live.
- No generar picks con datos incompletos o stale.
- Medir creditos y fallos por fuente.

## Operacion De Telegram

- Telegram real requiere autorizacion humana.
- Dry-run por defecto.
- Destino siempre enmascarado en informes.
- Dedupe obligatorio.
- Limite diario y horario.
- No enviar filler.
- No enviar picks con datos stale.
- Toda entrega debe guardar evidencia.

## Operacion De Stripe

- Modo test hasta certificacion completa.
- Webhook con firma e idempotencia.
- Activacion de membresia auditada.
- Cancelacion y reembolso con proceso humano.
- Ninguna accion de cobro desde automatizacion generica.

## Operacion De Backups

- Backup antes de release y antes de restores.
- Checksum registrado.
- Restore solo en entorno aislado salvo emergencia autorizada.
- Retencion definida.
- Copia offsite antes de beta ampliada.
- Prueba de lectura tras restore.

## Soporte

| Tipo | Tiempo objetivo beta | Owner |
| --- | --- | --- |
| Pago/membresia | <4h | Support Lead + Owner |
| Acceso/login | <8h | Support Lead |
| Telegram | <8h | Ops Lead |
| Datos deportivos | <24h | Data Lead |
| Incidente P0/P1 | inmediato | Owner + CTO |

## Checklist De Apertura Beta

- Cron sin blocker.
- Restore drill aislado.
- Stripe test completo.
- Telegram test controlado.
- Soporte visible.
- Politica de cancelacion.
- Juego responsable visible.
- Browser QA PASS.
- Sentinel PASS.
- Error budget definido.

## Siguiente Unica Accion

Convertir este playbook en checklist operativo recurrente dentro de la rutina de release: cada semana debe producir un estado PASS/PARTIAL/BLOCKED con owner y evidencia.
