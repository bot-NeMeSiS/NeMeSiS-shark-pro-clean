# V939 Mapa de motores y capacidades existentes

Este inventario define que se reutiliza antes de crear coordinacion nueva. V939 no sustituye motores validos ni replica su logica.

| Area | Capacidad existente confirmada | Integracion V939 |
|---|---|---|
| Operaciones | `company_operations_center_engine.py` | Fuente principal de salud operativa, readiness, incidencias y evidencia V938. |
| Recuperacion | `disaster_recovery_engine.py`, `operations_monitoring_engine.py` | Readiness y evidencias para simulaciones; nunca restore real. |
| Sentinel | Continuous Sentinel, Workflow y `sentinel_autopilot_engine.py` | Deteccion, clasificacion, prioridades y prompts; acciones peligrosas siguen bloqueadas. |
| Visual QA | `visual_company_worker_engine.py` | Evidencia visual y tareas, sin afirmar revision humana inexistente. |
| SHARK | SHARK safe mode y `shark_learning_engine.py` legado | Se conserva; V939 anade una vista de aprendizaje read-only y gobernada, sin modificar pesos. |
| Partidos | Lifecycle, realtime, false-live y stale filtering | Reglas de validez de origen para el pipeline de picks. |
| Cuotas | Odds freshness y usage guards | Bloqueo de cuotas ausentes, invalidas o stale. |
| Picks | Lifecycle, quality y grading existentes | V939 coordina un pipeline auditable; no publica ni liquida automaticamente. |
| Telegram | Calidad, dedupe, membresias, cards y entrega existentes | V939 prepara candidatos y variantes; no llama al envio real. |
| Clientes | Usuarios, sesiones, membresias y `user_activity` | Analitica agregada y minimizada, sin PII ni fingerprinting. |
| Pagos | Stripe y membership engines | Solo lectura de evidencia local; sin checkout, cobro, portal ni webhook artificial. |
| Datos | Data Marketplace, warehouse, provider y memory engines | Fuentes observables con freshness; sin llamadas externas durante render. |
| Backups | Vault, backup y recovery engines | Evidencia y simulacion, nunca reemplazo de DB. |
| Releases | Builder y auditor de release | Empaquetado V939 con exclusion de DB, secretos, caches y ZIPs internos. |

## Capacidades nuevas justificadas

V939 crea una capa de coordinacion, no otra fuente de verdad:

1. Snapshot empresarial con procedencia y estado de certificacion por senal.
2. Aprendizaje SHARK observacional basado exclusivamente en picks cerrados reales.
3. Pipeline de calidad de picks que expone motivos de bloqueo.
4. Analitica de producto agregada con controles de privacidad.
5. Gobernanza de experimentos sin activacion automatica.
6. Comparacion de versiones que distingue cambio de archivo de regresion demostrada.
7. Simulacion de recuperacion sin acciones destructivas.
8. Flujo de calidad que genera evidencia, prioridades, tareas y prompts, pero exige aprobacion para codigo y operaciones.

## Contrato de evidencia

Estados unicos V939:

- `VERIFIED`
- `PARTIALLY_VERIFIED`
- `NOT_CERTIFIED`
- `NOT_CONFIGURED`
- `STALE`
- `BLOCKED_BY_ACCESS`
- `HYPOTHESIS`
- `INSUFFICIENT_DATA`
- `REQUIRES_REVIEW`

Toda senal debe conservar fuente, tipo, fecha Madrid, frescura, version, entorno, confianza, evidencia y limitaciones.
