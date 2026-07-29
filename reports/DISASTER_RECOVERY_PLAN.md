# DISASTER RECOVERY PLAN

Fecha Madrid: 2026-07-29

Alcance: continuidad y recuperacion de NeMeSiS SHARK PRO.

Produccion modificada: false

Commit/push/deploy: no ejecutados

## Executive Summary

- **La continuidad actual es parcial.** El codigo esta en GitHub y Render usa disco persistente, pero la restauracion real no esta certificada como procedimiento repetible.
- **El mayor riesgo de recuperacion es creer que tener backups equivale a poder restaurar.** Para negocio real, un backup solo vale si se prueba en entorno aislado, con checksum, RTO/RPO y criterios de aceptacion.
- **Antes de escalar, NeMeSiS necesita backup offsite, restore drill y plan de operador secundario.** Sin eso, una incidencia de DB, Render o ausencia de Damian puede bloquear la empresa.

## Dependencias Criticas

| Dependencia | Impacto si falla | Estado |
| --- | --- | --- |
| Render web | App no disponible | PARTIAL |
| Render disk `/data/database.db` | Usuarios, sesiones, picks, membresias y estado operativo | HIGH_RISK |
| GitHub main | Codigo y rollback | PASS_LOCAL |
| SQLite DB | Persistencia central | PARTIAL |
| Telegram | Entrega premium/retencion | NOT_CERTIFIED |
| Stripe | Ingresos/membresias | NOT_CERTIFIED |
| APIs deportivas | Frescura y datos | PARTIAL |
| Damian/operador | Decision y soporte | SINGLE_POINT_OF_FAILURE |

## RTO Y RPO Propuestos

| Sistema | RTO beta | RTO publico | RPO beta | RPO publico |
| --- | ---: | ---: | ---: | ---: |
| Web app | 4h | 1h | 0 codigo perdido | 0 codigo perdido |
| DB usuarios/membresias | 8h | 2h | 24h max | 1h-4h max |
| Datos deportivos | 24h | 4h | 24h | 1h-4h |
| Telegram | 24h | 4h | mensajes no duplicados | mensajes no duplicados |
| Stripe/membresias | 4h | 1h | 0 cobros perdidos | 0 cobros perdidos |
| Soporte | 24h | 4h | tickets no perdidos | tickets no perdidos |

## Politica De Backup

### Minimo para beta

- Backup antes de cada release.
- Backup diario automatico.
- Checksum SHA-256.
- Restore mensual en entorno aislado.
- Retencion minima de 7 dias.
- Registro en Operations Center.

### Minimo para lanzamiento publico

- Backup horario o incremental para datos criticos.
- Copia offsite cifrada.
- Restore drill antes de cada release mayor.
- Prueba de integridad post-restore.
- Procedimiento documentado para Stripe/membresias.
- Segundo operador con acceso probado.

## Procedimiento De Restore Aislado

1. Crear copia de seguridad actual.
2. Copiar backup candidato a entorno temporal.
3. Verificar checksum.
4. Arrancar app local/staging con `DB_PATH` temporal.
5. Ejecutar `PRAGMA quick_check`.
6. Validar tablas criticas.
7. Ejecutar smoke de login, membresias, partidos, picks y admin.
8. Confirmar que no hay Telegram ni Stripe real.
9. Documentar RTO/RPO real medido.
10. Marcar backup como restaurable.

## Procedimiento De Perdida De DB En Produccion

- P0.
- Pausar writes si el servicio sigue vivo.
- No crear DB nueva vacia salvo modo emergencia explicito.
- Identificar ultimo backup valido.
- Preparar restore aislado primero.
- Comunicar estado si usuarios reales afectados.
- Ejecutar restore en produccion solo con autorizacion humana.
- Validar usuarios, membresias, picks y pagos.

## Procedimiento De Caida Render

- Confirmar si es app, deploy, region o proveedor.
- Consultar GitHub/main y ultimo SHA estable.
- No cambiar secretos.
- No forzar redeploy sin causa.
- Si Render falla largo tiempo: preparar proveedor alternativo solo con DB backup verificado.

## Procedimiento De GitHub No Disponible

- No desplegar cambios nuevos.
- Mantener app en Render.
- Usar ultimo ZIP certificado solo si existe y fue auditado.
- Registrar cambios localmente sin push.
- Reanudar sincronizacion cuando GitHub vuelva.

## Procedimiento De Ausencia Del Operador Principal

- Segundo operador debe conocer:
  - acceso GitHub;
  - acceso Render;
  - ubicacion de backups;
  - runbook P0/P1;
  - canal de soporte;
  - politica de no cobro/no Telegram sin autorizacion.
- Si no existe segundo operador, estado de continuidad empresarial: PARTIAL.

## Modo Degradado

| Falla | Modo degradado |
| --- | --- |
| API deportiva | Mostrar cache con frescura y limitaciones. |
| Telegram | Pausar envios, mantener app web. |
| Stripe | Pausar altas pagadas, mantener acceso existente. |
| DB parcial | Solo lectura o mantenimiento. |
| SHARK | Mostrar evidencia disponible sin analisis avanzado. |
| Cron | Mostrar datos existentes con stale claro. |

## Criterios De PASS

- Restore aislado ejecutado en menos de RTO beta.
- Checksum documentado.
- DB restaurada pasa quick_check.
- App funciona contra DB restaurada.
- No hay datos inventados.
- No hay Telegram/Stripe real durante prueba.
- Segundo operador puede seguir el runbook.

## Estado Actual

DISASTER RECOVERY READINESS: PARTIAL

La base existe, pero falta certificar restore aislado y offsite backup antes de beta ampliada o lanzamiento publico.
