# NeMeSiS SHARK PRO - Plan de continuidad de negocio

## Objetivos de recuperación

| Servicio/dato | Criticidad | RTO propuesto | RPO propuesto | Modo degradado |
|---|---|---:|---:|---|
| Identidad, usuarios, membresías | P0 | 2 h | 15 min | Login pausado; no crear DB vacía |
| Pagos/webhooks | P0 | 1 h | 0 eventos: Stripe debe poder reintentar/replay | Checkout pausado, plan conservado |
| DB principal | P0 | 2 h | 15 min | Read-only/maintenance |
| Producto público | P1 | 30 min | N/A | Página de estado y contenido estático |
| Datos deportivos | P1 | 2 h | 15 min para live; 60 min próximos | Última sync etiquetada o vacío seguro |
| Telegram | P1 | 4 h | Cola/delivery IDs sin pérdida | Pausado, app disponible |
| SHARK | P2 | 4 h | N/A | Modo seguro sin OpenAI |
| Admin/observabilidad | P1 | 1 h | 5 min eventos | Health externo/read-only |
| Histórico/track record | P1 | 4 h | 15 min después de grading | Lectura de snapshot verificado |

Estos RTO/RPO son objetivos empresariales; no están demostrados todavía.

## Dependencias y puntos únicos de fallo

| Dependencia | Fallo | Consecuencia | Mitigación requerida |
|---|---|---|---|
| Render web | Servicio/region | Caída total | Status externo, runbook, alternativa documentada |
| Render disk | Pérdida/mount | DB y backups locales | Backup cifrado off-site |
| GitHub | Indisponible/compromiso | No deploy/rollback desde origen | Clone/bundle seguro y SHA de release |
| SQLite | Lock/corrupción | Auth/datos/pagos afectados | WAL discipline, off-site, restore drill |
| API deportiva | Caída/stale | Sin agenda/live/picks | Cache con edad, vacío seguro, proveedor alterno evaluado |
| Telegram | Bot/API | Sin alertas | Cola retenida, app como canal primario |
| Stripe | API/webhook | Alta/cancelación incierta | Reintentos idempotentes y reconciliación |
| OpenAI | Caída/coste | SHARK avanzado indisponible | Modo seguro local |
| Persona administradora | Ausencia | Incidentes/release bloqueados | Acceso break-glass y segundo operador |

## Escenarios

### Render cae 1 hora

- Detener deploys y confirmar que DB disk no se toca.
- Publicar estado por canal independiente.
- No procesar manualmente pagos/Telegram duplicables.
- Restaurar servicio o rollback de código si la causa es release.
- Validar runtime, auth, DB, feed y webhooks antes de cerrar.

### Render cae 1 día

- Activar continuidad formal y comunicación periódica.
- Exportar/reconciliar eventos Stripe pendientes desde fuente oficial cuando vuelva.
- Mantener Telegram pausado salvo canal de estado autorizado.
- Evaluar proveedor alternativo de hosting desde release reproducible, sin mover DB sin plan.

### GitHub no está disponible

- Producción sigue operando.
- No hacer cambios no trazables.
- Usar copia local firmada solo para diagnóstico.
- Esperar recuperación salvo P0; para P0 usar procedimiento break-glass con revisión posterior.

### API deportiva caída

- Mantener páginas rápidas con última sync y/o estado seguro.
- Excluir live, picks y cuotas fuera de freshness.
- No aumentar polling agresivamente.
- Reanudar con backoff y reconciliar dedupe.

### Telegram falla

- Pausar worker y conservar delivery IDs/cola.
- Informar dentro de la app, no reenviar en masa al recuperar.
- Reconciliar destino, dedupe y límites antes de liberar.

### Stripe falla

- Pausar checkout/portal si el estado es incierto.
- Conservar plan actual hasta reconciliar evento firmado.
- No revocar acceso ni cobrar manualmente por suposición.

### Se pierde la DB

- P0; modo mantenimiento y congelación total de writes.
- No iniciar una DB vacía en la ruta esperada.
- Preservar volumen/logs, validar backup off-site y restaurar con doble aprobación.
- Reconciliar Stripe y Telegram después, no antes.

### Administrador no disponible

- Operador alternativo consulta runbook y monitor.
- Acceso break-glass de mínimo privilegio, custodiado fuera del repositorio.
- Acciones irreversibles siguen requiriendo segunda persona.

## Backups mínimos

1. Snapshot SQLite consistente cada 15-60 min según actividad.
2. Copia cifrada fuera de Render y fuera del repositorio.
3. Retención: diaria 30 días, semanal 12 semanas, mensual 12 meses, ajustada a legal.
4. Manifest SHA-256 y `PRAGMA integrity_check`.
5. Restore drill trimestral en entorno aislado.
6. Reconciliación de usuarios, membresías, picks, resultados y delivery IDs.

## Modo degradado

- Lectura pública y legal disponibles.
- Login solo si DB íntegra.
- Datos deportivos vacíos o con edad explícita.
- SHARK seguro sin proveedor externo.
- Telegram/checkout deshabilitados con explicación.
- Admin muestra causa, última evidencia y siguiente acción.

## Plan de emergencia

1. Nombrar IC y registrar SHA/runtime.
2. Aislar sistema afectado.
3. Proteger DB y secretos.
4. Elegir rollback de código o restauración de datos; nunca ambos por defecto.
5. Validar en orden: integridad -> auth -> membresías -> feed -> pagos -> Telegram.
6. Observación mínima P0: 24 h.

## Estado de madurez

- RTO/RPO: definidos aquí, no medidos.
- Backup local: código y prueba temporal disponibles.
- Backup off-site: no probado.
- Restore real: no probado.
- Proveedor alterno/DR regional: no documentado.
- Bus factor: crítico.

