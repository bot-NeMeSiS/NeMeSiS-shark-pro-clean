# NeMeSiS SHARK PRO - Automatización y guardrails

## Clasificación

| Proceso | Clase | Permitido automáticamente | Límite/guardrail | Aprobación humana |
|---|---|---|---|---|
| Health/runtime checks | Automático seguro | GET read-only | Timeout, redacción, sin PII | No |
| Route/link/Jinja/compile | Automático seguro | Validación | Sin efectos externos | No |
| Sentinel detección | Automático seguro | Abrir/deduplicar issue interno | Nunca borrar/restaurar/enviar/cobrar | No para detectar; sí para remediar |
| Sports sync | Automático con límites | Leer proveedor y escribir datos validados | Budget, backoff, dedupe, freshness, lock | Solo cambios de proveedor/ventana |
| Clasificación lifecycle | Automático con límites | Próximo/live/finalizado | Máquina de estados y evidencia | Excepciones manuales auditadas |
| Grading de picks | Automático con aprobación | Proponer settlement | Fuente oficial, idempotencia, discrepancy gate | Sí para discrepancias/correcciones |
| Generación de picks | Automático con aprobación | Candidato/borrador | Completo, cuota fresh, no publicación | Publicación final o política preaprobada |
| SHARK | Automático con límites | Contexto y abstención | Sin datos sintéticos, coste, timeout | No para respuesta; sí para cambiar políticas |
| Telegram cola/dedupe | Automático con límites | Preparar/entregar allowlist | Daily cap, kill switch, delivery ID | Mensaje masivo/test real inicial |
| Backups | Automático con límites | Crear, cifrar, verificar y copiar off-site | Retención, hash, integrity | No para crear; sí para borrar fuera de política |
| Restore DB | Exclusivamente humano | Ninguno | Doble aprobación, aislamiento, safety snapshot | Siempre |
| Deploy | Automático con aprobación | Auto-deploy tras merge autorizado | CI, backup SHA, no force | Merge/release GO |
| Rollback código | Automático con aprobación | Preparar/recomendar | Solo SHA conocido, DB intacta | Incident Commander |
| Cambios de membresía | Automático con límites | Evento Stripe firmado/idempotente | Reconciliación | Grants/revocaciones excepcionales |
| Cobros | Automático con aprobación previa | Stripe sobre consentimiento | Idempotencia, catálogo, webhook | Config/precio; no por incidente |
| Reembolsos | Exclusivamente humano | Ninguno | Doble revisión y evidencia | Siempre |
| Exportaciones con PII | Automático con aprobación | Generar tras autorización | Cifrado, expiración, audit log | Siempre |
| Limpieza técnica | Automático con límites | Cache/tmp expirado | Allowlist, dry-run, no tracked/runtime | Política aprobada |
| Borrado de usuario | Exclusivamente humano asistido | Workflow tras verificación | Retención legal, cascada y audit | Siempre |
| Comunicación de incidente | Automático con aprobación | Borrador interno | Sin PII, hechos confirmados | Publicación externa |

## Guardrails obligatorios

### Identidad y autorización

- Secretos solo por headers/canales apropiados, nunca URL.
- Roles server-side y mínimo privilegio.
- Reautenticación para acciones irreversibles.
- Doble control para restore, reembolso, rotación y masivos.

### Datos

- Provenance, timestamp y completeness por registro.
- Freshness gate antes de KPI, API, card, SHARK o Telegram.
- Idempotency key y dedupe por proveedor/partido/evento.
- Cuota 0/stale/incompleta bloqueada.
- Estado seguro si no hay evidencia.

### Coste y disponibilidad

- Budget diario/mensual por API/IA.
- Alertas 70/85/95%.
- Backoff exponencial con jitter.
- Circuit breaker; no proveedor durante render.
- Polling 45 s con live, 180 s sin live; cache 15 s como diseño esperado.

### Efectos externos

- Dry-run por defecto.
- Allowlist de destinos Telegram.
- Daily cap y kill switch visible en admin.
- Stripe test antes de live; nunca cargos en QA.
- Deploy solo desde SHA trazable.

### Auditoría

- Actor, acción, objeto, resultado y timestamp.
- No guardar secreto, cookie, payload completo ni PII innecesaria.
- Logs append-only fuera de DB operativa para eventos críticos.
- Correlation ID entre cron, sync, pick, Telegram y webhook.

## Kill switches mínimos

1. Pausar sports sync sin ocultar stale.
2. Bloquear publicación de picks.
3. Pausar Telegram conservando cola/dedupe.
4. Forzar SHARK modo seguro.
5. Pausar checkout/portal sin revocar planes.
6. Modo mantenimiento/read-only.

## Prohibiciones

- Auto-restaurar DB.
- Auto-reembolsar o cobrar.
- Auto-rotar secretos sin runbook.
- Auto-publicar pick incompleto.
- Auto-enviar masivo tras recuperación.
- Auto-corregir ROI sin fuente y revisión.
- Auto-eliminar reportes/backups sin retención y manifest.

## Pruebas de automatización

- Doble cron concurrente produce una sola ejecución.
- Replay de webhook produce un solo entitlement.
- Fallo de proveedor no genera llamadas en bucle.
- Cola Telegram reanudada no duplica.
- Restore requiere dos aprobaciones y backup válido.
- Kill switch bloquea el efecto pero conserva diagnóstico.

