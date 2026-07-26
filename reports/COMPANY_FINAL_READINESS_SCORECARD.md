# NeMeSiS SHARK PRO - Scorecard final de preparación

Escala: 0 inexistente, 5 funcional pero no certificada, 8 sólida para beta, 10 operación madura y demostrada.

| Área | Nota | Evidencia | Principal problema | Acción para +1 | Riesgo de no actuar |
|---|---:|---|---|---|---|
| Producto | 8.0 | Superficies completas, copy responsable | Evidencia real E2E desigual | Beta observada y métricas de activación | Decidir por percepción, no uso |
| Diseño | 8.5 | Capturas coherentes y marca propia | Repetición de empty states/hero alto | Segunda pasada basada en usuarios | Fatiga visual menor |
| Móvil | 8.0 | Header/bottom nav/cards específicos | Tabs/nav horizontales cortados | Device QA 5 tamaños y teclado | Fricción en pantallas pequeñas |
| Backend | 6.5 | 664 reglas, fallbacks, checks | Monolito ~1.2 MB y rutas legacy | Extraer un dominio con tests | Regresión amplia y lentitud de cambio |
| Base de datos | 5.5 | SQLite íntegra, legacy/lock tests | DR/off-site y conexión abierta | Restore drill + cerrar handles | Pérdida/locks |
| Datos deportivos | 6.0 | Gates de completitud/freshness | Producción fresca no certificada | SLO externo de sync/freshness | Daño de confianza |
| Picks | 7.0 | Lifecycle, quality gate, track record | Settlement real no certificado | Reconciliar muestra real y grading | ROI incorrecto |
| Telegram | 5.0 | Cola, dedupe, dry-run | Webhook sin auth y envío real no certificado | Secret header + allowlist test | Abuso/duplicados |
| SHARK | 7.0 | Modo seguro y benchmark candidato | Hotfix no confirmado en main/prod | Integrar/certificar con 10 mediciones | Lentitud/resultado inconsistente |
| Pagos | 5.0 | Firma/idempotencia y motor local | E2E real no certificado | Stripe test matrix/reconcile | Cobro/membresía incorrecta |
| Membresías | 5.5 | FREE/PRO/ELITE implementados | ELITE+ y precios inconsistentes | Catálogo único | Promesa contractual confusa |
| Seguridad | 5.0 | Hash, CSRF, rate limits, signed Stripe | Secret Guard/endpoints/cookies | Cerrar SEC-03 a SEC-07 | Compromiso/abuso |
| Privacidad | 4.0 | Textos y minimización parcial | Posible PII pública y DSAR ausente | Triage + retención/DSAR | Riesgo legal P0 |
| Automatización | 6.0 | Workers, dry-run, cron sports | Ejecución real parcial/no alertada | Ledger/dead-man/kill switches | Fallo silencioso |
| Observabilidad | 6.0 | Sentinel/health/runtime/QA | Sin synthetic/pager/APM probado | Monitor externo | Degradación invisible |
| Backups | 4.0 | Creación/checksum/safety backup | Mismo disco, restore no probado | Off-site + drill | Pérdida total |
| Recuperación | 3.5 | Rollback y código de restore | RTO/RPO no medidos | Simulacro P0 | Recuperación improvisada |
| GitHub/CI | 5.0 | Workflows y checks amplios | Repo público pesado, gates divergentes | Secret Guard + entorno hermético | Deploy inseguro/bloqueado |
| Render | 5.0 | Blueprint, disk, health, cron | Estado real no alcanzable/certificado | SHA/runtime synthetic | Versión antigua/degradada |
| Soporte | 5.5 | Ruta/UX y copy | Sin ticketing/SLA/guardia | Proceso beta y owner | Mala retención |
| Modelo de negocio | 5.5 | Propuesta diferenciada | Sin unit economics/validación | Cohorte beta y coste por usuario | Margen desconocido |
| Escalabilidad | 4.5 | Caches y guards | SQLite, un worker, bus factor | Load test y umbral de migración | Colapso al crecer |
| Preparación comercial | 5.0 | Producto presentable | Legal, pagos, soporte y evidencia | Cerrar gates de pago | Vender antes de poder cumplir |
| Preparación para beta | 5.0 | Visual/funcional local fuerte | P0 privacidad/DR | Cerrar P0 y certificar prod | Incidente con primeros usuarios |
| Preparación para producción | 4.0 | Base desplegable y versionada | Operación real no certificada | 7 días de production gate | Falsa sensación de seguridad |

## Resumen ponderado

- Experiencia y marca: **8.2/10**.
- Ingeniería y datos: **6.1/10**.
- Operaciones, seguridad y recuperación: **4.8/10**.
- Comercial y negocio: **5.2/10**.
- Preparación total estimada: **5.8/10**.

## Gates

| Gate | Estado | Motivo |
|---|---|---|
| Demo guiada | PASS | Producto visual y fallbacks sólidos |
| Beta privada gratuita | BLOCKED | P0 privacidad/DR y producción no certificada |
| Beta privada de pago | BLOCKED | Añade pagos/legal/soporte |
| Lanzamiento público | BLOCKED | Observabilidad, escala y continuidad insuficientes |

## Acción que más sube la nota

Cerrar el paquete de confianza operativa: triage de repositorio público, backup off-site con restore drill y monitor externo de producción. No añade funciones, pero transforma la capacidad de operar y recuperarse.

