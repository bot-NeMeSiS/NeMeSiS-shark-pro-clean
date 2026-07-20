# NeMeSiS SHARK PRO - Catálogo integral de fallos

## Criterios

- Probabilidad: B baja, M media, A alta.
- Impacto: B bajo, M medio, A alto, C catastrófico.
- Severidad: P0 caída/pérdida/cobro/seguridad grave; P1 función crítica; P2 degradación; P3 menor; P4 preventiva.
- MTTD objetivo: tiempo máximo para detectar.
- Riesgos: E económico, R reputacional, L legal; B/M/A/C.
- Toda automatización que escriba, envíe, cobre, restaure o borre requiere los guardrails de `COMPANY_AUTOMATION_GUARDRAILS.md`.

## Plataforma, release y GitHub

| ID / fallo | Cat. P/I/Sev | Síntoma visible / técnico | Detección actual y MTTD | Responsable; auto / humano | Datos/clientes; E/R/L | Contención, recuperación y rollback | Cierre, prevención, test y alerta |
|---|---|---|---|---|---|---|---|
| F01 Render no responde | Infra M/C/P0 | App inaccesible / timeout DNS-TLS | Health externo no probado; objetivo 2 min | DevOps; auto alerta / IC decide | Todos; A/C/M | Estado público, congelar cambios; recuperar servicio o proveedor; rollback no aplica si plataforma | 30 min estable; synthetic 1 min, alerta pager |
| F02 Render 502 | Infra M/A/P1 | 502 / proceso no escucha, crash o timeout | Logs + health; objetivo 2 min | DevOps+Backend; restart limitado / humano | Todos; A/A/B | Modo mantenimiento; inspeccionar start/memoria; rollback SHA si cambio | 0 502 30 min; smoke post-start y alerta 5xx |
| F03 Deploy defectuoso | Release M/A/P1 | Rutas/asset fallan / SHA nuevo con errores | CI+postdeploy parcial; 5 min | Release+QA; auto gate / humano rollback | Todos; A/A/M | Pausar deploys; volver a SHA conocido sin DB restore | Runtime/critical smoke verdes; canary y rollback test |
| F04 GitHub Actions falla | CI A/M/P2 | PR bloqueado / job rojo | GitHub inmediato | QA+CI; no auto-merge / humano corrige | Release; M/M/B | No desplegar; reproducir herméticamente | Logs explicados, rerun verde; test de workflow |
| F05 Main tiene commit incorrecto | SCM B/A/P1 | Regresión general / SHA no aprobado | Review/checks; objetivo 5 min tras deploy | Release; alerta / propietario revierte | Todos; A/A/M | Congelar main; revert normal al backup | SHA correcto servido; branch protection, backup previo |
| F06 PR bloqueado | SCM M/M/P3 | Cambio no avanza / rules/check faltante | GitHub inmediato | Release; diagnóstico / owner acción | Sin clientes directos; M/B/B | No saltar protección; corregir causa/config autorizada | Mergeable y checks verdes; auditoría de rules |
| F07 Auto-Deploy no ejecuta | DevOps M/A/P1 | Main nuevo, producción antigua | SHA monitor; hoy no probado; objetivo 5 min | DevOps; alerta / deploy manual autorizado | Todos futuros; M/A/B | No declarar release; comprobar hook/branch | Render SHA=main; integration test del pipeline |
| F08 Render sirve SHA antiguo | DevOps M/A/P1 | Fix ausente / runtime desalineado | Runtime version, falta monitor SHA; 2 min | DevOps+Release; alerta / redeploy | Todos; A/A/B | Marcar producción no certificada; redeploy sin tocar disco | SHA exacto 3 lecturas; endpoint de commit firmado |

## Base de datos, identidad y persistencia

| ID / fallo | Cat. P/I/Sev | Síntoma visible / técnico | Detección actual y MTTD | Responsable; auto / humano | Datos/clientes; E/R/L | Contención, recuperación y rollback | Cierre, prevención, test y alerta |
|---|---|---|---|---|---|---|---|
| F09 DB bloqueada | DB M/A/P1 | Lentitud/error seguro / `database is locked` | Retry/logs/Sentinel parcial; 2 min | DB+Backend; retry acotado / humano | Sesiones/datos; M/A/M | Reducir writers, modo read-only; liberar proceso, no borrar WAL | 0 locks 30 min; concurrency test y alerta count |
| F10 DB corrupta | DB B/C/P0 | Datos inaccesibles / integrity_check falla | Health no continuo; objetivo 5 min | DB+IC; read-only / doble aprobación restore | Todos los datos; C/C/C | Detener writes; copiar evidencia; restaurar backup verificado | Integridad y reconciliación; restore drill trimestral |
| F11 Disco persistente desconectado | Infra B/C/P0 | Datos desaparecen / path efímero o mount ausente | Runtime/DB health parcial; 2 min | DevOps+DB; fail closed / humano | Todos; C/C/C | Mantenimiento, no inicializar DB vacía; remount/rollback config | Mount y usuarios persisten restart; startup guard |
| F12 DB_PATH incorrecto | Config M/C/P0 | App vacía / DB nueva | Runtime expone path; objetivo startup | DevOps+DB; startup abort / humano | Todos; C/C/A | No escribir; restaurar env/mount, reiniciar | Path esperado+integridad; config test |
| F13 Datos de usuarios desaparecen | DB B/C/P0 | Cuentas/planes faltan / rows caen | KPI/anomaly no externo; 2 min | DB+Security+Support; freeze / humano | PII/membresías; C/C/C | Desactivar altas/cobros; snapshot; restore/reconcile | Recuento y muestras reconciliados; backup off-site |
| F14 Sesiones dejan de funcionar | Auth M/A/P1 | Logout/login recurrente / key/cookie cambia | Auth smoke; 5 min | Backend+Security; fallback login / humano | Todos autenticados; A/A/M | Preservar datos, informar; restaurar key/config sin exponerla | Login/session/logout 30 min; canary auth |
| F15 Registro o login fallan | Auth M/A/P1 | No se puede entrar / 500, CSRF, DB | Route smoke local; producción no continua; 2 min | Backend+Support; alerta / humano | Nuevos/actuales; A/A/M | Congelar campañas; mensaje y soporte; fix/rollback | Flujos real-test pasan; synthetic seguro |

## Datos deportivos y APIs

| ID / fallo | Cat. P/I/Sev | Síntoma visible / técnico | Detección actual y MTTD | Responsable; auto / humano | Datos/clientes; E/R/L | Contención, recuperación y rollback | Cierre, prevención, test y alerta |
|---|---|---|---|---|---|---|---|
| F16 API deportiva no responde | Provider A/A/P1 | Agenda vacía segura / timeout/error | Guards+sync logs; objetivo 5 min | Datos+DevOps; backoff/cache / humano proveedor | Feed; A/A/B | Servir cache con edad o vacío; cambiar ventana/proveedor autorizado | Sync recuperada y freshness SLO; contract test |
| F17 API devuelve datos antiguos | Data M/A/P1 | Eventos obsoletos / timestamp viejo | Freshness gate local; 5 min | Datos; excluir auto / humano investiga | Feed; A/C/M | No publicar; marcar stale; resync controlada | 0 stale público 24 h; fixture de edad |
| F18 Falsos partidos live | Data M/C/P0 | Live inexistente / status sin evidencia | V937 gate+Sentinel; 2 min | Realtime+Trust; excluir auto / humano | Todos; A/C/M | Vaciar arrays/KPI/Telegram/SHARK; conservar evidencia | Live con marcador/minuto/fase real; regression test |
| F19 Finalizados como próximos | Lifecycle M/A/P1 | Agenda engañosa / estado/fecha mal | Lifecycle checks; 5 min | Sports Data; reclasificar / humano | Feed; M/A/B | Excluir y recalcular; corregir mapping | Cero solapes; test de transición |
| F20 Partidos duplicados | Data M/M/P2 | Cards repetidas / dedupe key falla | Dedupe/reportes; 15 min | Sports Data; dedupe seguro / humano | Feed; M/A/B | Ocultar duplicado de menor calidad; reindexar | Clave canónica y 0 duplicados; fixture multi-provider |
| F21 Faltan escudos/logos | Asset A/M/P3 | Fallback visible / URL rota | Browser QA; 24 h | Frontend+Data; fallback / humano licencia | Visual; B/M/L(M por IP) | Fallback canónico; no inventar logo | 0 asset 404; visual test y license registry |
| F22 Cuotas obsoletas | Odds M/A/P1 | Cuota activa vieja / edad incorrecta | Freshness rules; 5 min | Odds+Trust; excluir/etiquetar / humano | Picks; A/C/M | Bloquear publicación/Telegram; resync | Timestamp/fuente válidos; boundary tests 15/60 min |
| F23 Créditos API agotados | Cost M/A/P1 | Feed no actualiza / 429/quota | Usage guard parcial; objetivo 10 min | Data+Finance; backoff/budget / humano compra | Feed; A/A/B | Cache/empty seguro; detener llamadas no críticas | Presupuesto <80%, alertas 70/85/95% |

## Telegram y automatización

| ID / fallo | Cat. P/I/Sev | Síntoma visible / técnico | Detección actual y MTTD | Responsable; auto / humano | Datos/clientes; E/R/L | Contención, recuperación y rollback | Cierre, prevención, test y alerta |
|---|---|---|---|---|---|---|---|
| F24 Telegram no envía | Telegram M/A/P1 | Sin alerta / delivery error | Logs/queue, no alerta probada; 5 min | Telegram Ops; retry limitado / humano | Suscriptores; A/A/B | Pausar promesa; retener cola; reautorizar bot | Dry-run+mensaje test autorizado; delivery SLO |
| F25 Telegram duplica mensajes | Telegram M/A/P1 | Dos o más mensajes / dedupe falla | Dedupe logs; 2 min | Telegram Ops; kill switch / humano | Suscriptores; M/C/M | Pausar worker; marcar delivery IDs; no reenviar | 0 duplicados 7 días; idempotency test |
| F26 Telegram envía contenido incorrecto | Content B/C/P0 | Pick/dato erróneo / filtro omitido | Quality gate; no revisión real continua | Editorial+Trust; bloquear incompletos / humano | Todos receptores; A/C/A | Stop envíos, corrección transparente; retirar cola | Fuente y revisión demostradas; golden-message tests |
| F27 Telegram destino equivocado | Security B/C/P0 | Mensaje a canal no autorizado / chat ID mal | Config audit; objetivo antes de envío | Telegram+Security; allowlist / doble humano | PII/contenido; A/C/C | Kill switch, revocar token, notificar | Allowlist y test técnico único; config fingerprint alert |
| F28 Cron no ejecuta | Automation M/A/P1 | Datos stale / tick ausente | Cron health parcial; objetivo 20 min | DevOps+Automation; alertar/retry / humano | Feed/jobs; A/A/B | No simular frescura; ejecutar dry-run y reparar schedule | Dos ticks sucesivos SUCCESS; heartbeat alert |
| F29 Cron ejecuta varias veces | Automation M/A/P1 | Duplicados/costes / concurrencia | Dedupe parcial; 2 min | Automation+DB; lock/idempotencia / humano | Feed/costes; A/A/M | Pausar instancias, conservar una lease | Una ejecución por ventana; concurrency test |
| F30 AUTOMATION_SECRET no coincide | Security M/A/P1 | 403 de cron / config drift | HTTP status/logs; 5 min | DevOps+Security; no fallback / humano rota | Jobs; M/M/B | No pasar por URL; reconciliar env segura | Header autorizado pasa, sin secreto 403 |

## SHARK, Sentinel y observabilidad

| ID / fallo | Cat. P/I/Sev | Síntoma visible / técnico | Detección actual y MTTD | Responsable; auto / humano | Datos/clientes; E/R/L | Contención, recuperación y rollback | Cierre, prevención, test y alerta |
|---|---|---|---|---|---|---|---|
| F31 SHARK lento | Performance M/A/P1 | >4 s / N+1, write o red en GET | Benchmark local; producción no continua; 5 min | SHARK+Perf; cache/fallback / humano | Usuarios SHARK; M/A/B | Modo seguro; desactivar llamada bloqueante | p95 objetivo y 0 writes; route benchmark |
| F32 SHARK 500 | Product M/A/P1 | Error / excepción contexto | Error handler/Sentinel parcial; 2 min | SHARK+Backend; fallback seguro / humano | Usuarios SHARK; M/A/M | Modo seguro, no conversación; rollback fix | 0 500 24 h; provider-down test |
| F33 SHARK muestra datos incompletos | Trust M/C/P0 | Recomendación engañosa / gate omitido | Data Trust checks; 2 min | SHARK+Sports Trust; abstener / humano | Picks/partidos; A/C/A | Ocultar recomendación y explicar ausencia | Contexto completo y fuente; negative fixtures |
| F34 Sentinel deja de ejecutar | Observability M/A/P1 | Sin alerta / heartbeat stale | No monitor externo probado; 15 min | Sentinel+DevOps; watchdog / humano | Toda operación; M/A/M | Considerar sistema sin vigilancia; activar checks manuales | Heartbeat y prueba de fallo; dead-man alert |
| F35 Sentinel falso positivo | QA A/M/P2 | Incidencias ruido / regla sensible | Revisión humana | QA; dedupe/suppress temporal / humano | Operaciones; M/M/B | No auto-remediar destructivamente; calibrar | Precision medida; corpus positivo/negativo |
| F36 Sentinel omite fallo real | QA M/A/P1 | “10/10” con riesgo / cobertura incompleta | Auditoría externa; MTTD indeterminado | QA+Security; defense-in-depth / humano | Todos; A/C/A | No usar score como único gate; activar monitor externo | Test de inyección detectado; cobertura explícita |

## Stripe y membresías

| ID / fallo | Cat. P/I/Sev | Síntoma visible / técnico | Detección actual y MTTD | Responsable; auto / humano | Datos/clientes; E/R/L | Contención, recuperación y rollback | Cierre, prevención, test y alerta |
|---|---|---|---|---|---|---|---|
| F37 Stripe no confirma pago | Payment M/C/P0 | Cobrado sin plan / webhook ausente | Webhook logs no certificados; 2 min | Payments+Support; reconcile / humano | Pago/membresía; C/C/C | No duplicar cargo; preservar receipt; reconciliar evento | Stripe y DB coinciden; webhook replay test |
| F38 Webhook Stripe falla | Payment M/A/P1 | Plan no cambia / 4xx/5xx | Firma/logs; 2 min | Payments+Backend; retry idempotente / humano | Suscripciones; A/A/A | Cola/replay seguro; no aceptar sin firma | 2xx e idempotencia; fixture firmado test |
| F39 Membresía no se activa | Entitlement M/A/P1 | Usuario FREE tras pago / mapping | Reconciliation pendiente; 5 min | Payments+Support; reconcile / humano | Cliente pagado; A/C/A | Acceso provisional manual auditado si evidencia | Tier correcto, expiry/origin guardados |
| F40 Membresía no se cancela | Entitlement M/A/P1 | Sigue premium/cobro / cancel event | Webhook/cron | Payments; reconcile / humano | Cliente; A/A/A | Detener renovación, respetar periodo; no borrar cuenta | Estado Stripe/DB coincide; cancel test |
| F41 Cliente ve funciones no pagadas | Authorization M/A/P1 | Acceso premium / check solo UI | Entitlement tests parciales; 5 min | Backend+Security; deny server-side / humano | Ingresos; A/A/M | Cerrar API, conservar sesión | Matrix tier/ruta; authz integration test |
| F42 Cliente pierde funciones pagadas | Entitlement M/A/P1 | 403 indebido / drift | Support/reconciliation; 5 min | Payments+Support; restore verified / humano | Cliente pagado; A/C/A | Acceso temporal con evidencia; reconciliar | Entitlement y recibo coinciden; renewal test |

## Seguridad, privacidad, backup y experiencia

| ID / fallo | Cat. P/I/Sev | Síntoma visible / técnico | Detección actual y MTTD | Responsable; auto / humano | Datos/clientes; E/R/L | Contención, recuperación y rollback | Cierre, prevención, test y alerta |
|---|---|---|---|---|---|---|---|
| F43 Permisos cliente/admin cruzados | Authz B/C/P0 | Cliente ve admin / guard ausente | Route tests/Browser QA; 2 min | Security+Backend; deny / humano | PII/admin; C/C/C | Revocar sesiones, cerrar ruta, logs | Matriz 401/403/200; role tests |
| F44 Información técnica expuesta | Security M/A/P1 | Paths/flags visibles / runtime verboso | Manual/Secret Guard roto; 24 h | Security+Backend; redacción / humano | Internals; M/A/M | Minimizar endpoint público; rotar si secreto | Public response allowlist; snapshot test |
| F45 Secreto expuesto | Security M/C/P0 | Token visible / repo/log/URL | Secret Guard roto; MTTD indeterminado | Security+IC; revoke / humano propietario | Sistemas/PII; C/C/C | Revocar, contener historial/logs, evaluar abuso | Rotación y scan limpio; canary/secret scan |
| F46 Incidente privacidad | Privacy M/C/P0 | PII accesible / repo/export/log | Sin DLP probado; MTTD indeterminado | DPO+Security+Legal | PII; C/C/C | Restringir acceso, preservar evidencia, evaluar notificación | Alcance/cierre legal; privacy tests/retention |
| F47 Backup inexistente/inválido | DR M/C/P0 | No puede restaurar / falta o hash falla | Local checksum; no off-site monitor | DB+Ops; alerta / doble humano | Todos; C/C/C | Detener cambios críticos; crear copia validada | Restore drill y copia off-site; daily backup SLO |
| F48 Restauración defectuosa | DR B/C/P0 | Datos parciales / schema mismatch | No prueba real; solo temporal | DB+IC; nunca auto / doble humano | Todos; C/C/C | Volver a safety backup, read-only | Integridad, counts, auth y app smoke; quarterly drill |
| F49 UI móvil rota | UX M/M/P2 | Overflow/CTA oculto | Browser QA manual; por release | Mobile+QA; no auto-fix / humano | Móviles; M/A/B | Feature fallback/rollback CSS | 5 viewports sin overflow; visual regression |
| F50 Navegación duplicada | UX M/M/P2 | Dos navs / shells conflictivos | Browser QA+Navigation Integrity | Frontend+QA; detect / humano | Todos; M/M/B | Ocultar shell incorrecto; rollback CSS/template | Cliente/admin/mobile separados; screenshot test |
| F51 Botón destino incorrecto | UX M/M/P2 | Acción no funciona / href/handler | Link audit; por commit | Frontend+QA; block release / humano | Flujo afectado; M/M/B | Deshabilitar con explicación; corregir target | Click smoke y 0 broken actions |
| F52 Datos/estados inventados | Trust B/C/P0 | Métrica falsa / fallback sintético | Guards/checks; release | Trust+Data; reject auto / humano | Todos; C/C/C | Retirar contenido, informar y corregir fuente | Provenance por dato; negative tests |
| F53 Fallo silencioso | Observability M/A/P1 | Datos no cambian / excepción absorbida | Sentinel parcial; indeterminado | Ops+Owner; heartbeat / humano | Variable; A/A/M | Declarar degradación, activar diagnóstico | Evento observable+alerta; chaos test |
| F54 Saturación de logs | Operations M/A/P1 | Disco/DB lleno / crecimiento | Sin budget continuo probado | Ops+DB; rotate/retention / humano | Todos; A/A/M | Reducir nivel, archivar sin borrar evidencia legal | <70% uso y retención; load test |
| F55 Degradación progresiva | Perf A/A/P1 | Latencia creciente / DB/CSS/cache | Benchmarks puntuales; 15 min objetivo | Performance+Ops; alert / humano | Todos; A/A/B | Limitar trabajos, cache seguro; rollback reciente | p95/SLO 24 h; trend alert |
| F56 API externa cambia | Dependency M/A/P1 | Parseo falla / contrato nuevo | Contract checks no continuo | Integration+Data; fail closed / humano | Feed/pago/IA; A/A/M | Fallback, pin versión, adaptar | Contract suite y sandbox; error-rate alert |
| F57 Librería Python incompatible | Dependency M/A/P1 | Build/import falla | CI compile; inmediato | Architecture+CI; block / humano | Deploy; M/M/B | No desplegar; pin/rollback | Clean install Python 3.11.9; lockfile test |
| F58 Error timezone | Data M/A/P1 | Día/hora incorrectos / UTC local | Madrid checks; release | Sports Data+QA; exclude ambiguous / humano | Feed/picks; M/A/M | No publicar cerca de borde; corregir conversion | DST fixtures; clock/timezone alert |
| F59 Error horario Madrid | Data M/A/P1 | Hora cliente errónea / offset/DST | `check_madrid_times`; release | Sports Data+QA | Feed; M/A/M | Mostrar timestamp con zona; reprocess | DST winter/summer fixtures |
| F60 Pick/resultado liquidado mal | Financial/Trust M/C/P0 | ROI/estado erróneo / grader mapping | Lifecycle checks parciales; 2 min tras grade | Editorial+Data Trust; freeze grading / doble humano | Track record/clientes; C/C/A | Pausar publicación/ROI, revertir settlement auditado | Fuente oficial, cuatro ojos, replay test, discrepancy alert |

## Lectura global

- P0: 17 escenarios potencialmente catastróficos; no significa que estén activos, sino que exigen controles preventivos y runbooks.
- P1: mayoría de fallos de disponibilidad, identidad, datos e integraciones.
- P2/P3: experiencia, mantenibilidad y ruido operativo.
- Los P0 activos o plausibles en el corte se reducen a dos riesgos de empresa: posible exposición pública sin clasificar y recuperación off-site no demostrada.

