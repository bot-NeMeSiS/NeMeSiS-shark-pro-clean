# NeMeSiS SHARK PRO - Auditoría de operaciones

## Modelo operativo actual

La empresa combina automatización extensa con una dependencia humana alta. El código contiene centros de control, workers y checks, pero muchas ejecuciones son manuales, dry-run o locales. La operación real de Render, Telegram, Stripe y la DB persistente no quedó certificada en este corte.

## Paneles administrativos

| Panel | Controla/muestra | Efectos | Protección observada | Rollback/auditoría | Necesita humano |
|---|---|---|---|---|---|
| Dashboard | KPIs, estado, siguiente acción | Navegación | Sesión admin | Logs parciales | Sí para decisiones |
| Usuarios | cuentas, plan, acceso | Cambios de usuario/plan | Admin + CSRF | Auditoría variable | Sí |
| Membresías | FREE/PRO/ELITE, origen | Upgrade/downgrade | Admin + CSRF | Motor conserva estado | Sí en grants/revocación |
| Pagos | Stripe, facturas, fallos | Potencialmente financiero | Admin; webhook firmado | Idempotencia | Exclusivamente humano para reembolsos/cargos |
| Picks | publicación, grading, estado | Visible a clientes/Telegram | Admin | Historial parcial | Sí para publicar dudosos |
| Partidos/Data Center | sync, completos/incompletos | Escribe datos deportivos | Admin/cron | Dedupe y estados | Automático con límites |
| Realtime | frescura, live, polling | Afecta contenido público | Admin | Guardas de stale | Automático con límites |
| Telegram Command Center | cola, dedupe, envíos | Mensaje externo | Admin y token | Delivery logs | Sí para masivos/pruebas reales |
| Automation Workforce | jobs, dry-run, cola | Puede ejecutar tareas | Admin/secret | Outbox/logs | Sí para acciones manuales |
| Daily Automation | ticks y resultados | Jobs múltiples | Secret/admin | Registro de ejecución | Automático con límites |
| Sentinel | issues y score | Registra/propone | Admin | Dedupe | Humano para remediar |
| Navigation Integrity | rutas/enlaces | Read-only/dry-run | Admin | Reportes | Automático seguro |
| Launch Certification | gate de salida | No debería desplegar por sí solo | Admin | Reportes | Exclusivamente humano |
| Backups/Data Vault | crear, borrar, restaurar | Irreversible/alto impacto | Admin + CSRF | Safety backup parcial | Doble aprobación necesaria |
| Runtime/System | versión, paths, health | Diagnóstico | Parte pública/parte admin | Logs | Read-only |

## Procesos críticos y madurez

| Proceso | Estado | Dependencia humana | Riesgo |
|---|---|---|---|
| Deploy | Parcialmente automatizado | Alta por PR/rules/Render | SHA divergente o deploy no iniciado |
| Sports sync | Declarado cada 15 min | Media | No hay evidencia real continua |
| Grading de picks | Código disponible | Media | Liquidación incorrecta si lifecycle diverge |
| Telegram | Cola y dedupe | Alta para certificar | Destino/duplicados |
| Stripe | Webhook/motor | Alta para certificar | Membresía/cobro incorrecto |
| Backup | Código local | Alta | Misma zona de fallo y restore no probado |
| Incident response | Reportes/runbooks dispersos | Muy alta | Conocimiento en una persona |
| Soporte | UI y legales presentes | Muy alta | Sin SLA, ticketing o guardia probados |

## Cron y scheduler

Confirmado:

- `render.yaml` declara sports sync cada 15 minutos.
- Rutas de automatización rechazan peticiones sin autorización.
- Master tick responde correctamente en un dry-run con secreto temporal de test.

No probado:

- Último tick/next tick real de Render.
- Telegram tick, grading, backups, Sentinel y daily automation como jobs externos independientes.
- Alertas cuando un cron no registra ejecución.
- Protección contra doble scheduler en más de una instancia.

## Gestión de cambios

El proceso dispone de versiones, ZIP, deploy root, checks y rollback documental. Sin embargo, hay ramas/PR candidatos no integrados y el repositorio contiene gran cantidad de evidencia histórica. Antes de escalar se necesita un release gate único:

1. Backup lógico y SHA de rollback.
2. Tests herméticos.
3. Secret Guard obligatorio.
4. Merge trazable.
5. Render sirve el mismo SHA.
6. Smoke real y 30-60 minutos de observación.
7. Cierre del incidente/release.

## Soporte y operación humana

- No se encontró un sistema de tickets/SLA integrado.
- No hay guardia, rotación ni sustituto documentado con accesos de emergencia.
- No hay página de estado externa confirmada.
- Los mensajes seguros en producto son buenos, pero no sustituyen comunicación de incidentes.

## Acciones operativas prioritarias

1. Triage de privacidad del repositorio público.
2. Backup off-site y simulacro de restauración.
3. Monitor externo de runtime/SHA/5xx/frescura.
4. Reconciliar CI, Secret Guard y PR candidatos.
5. Certificar cron real con evidencia de 24 horas.
6. Certificar Stripe y Telegram en entornos seguros.
7. Nombrar Incident Commander alternativo.
8. Definir SLA de soporte y comunicación.

