# NeMeSiS SHARK PRO - Registro de riesgos

Escala: probabilidad e impacto de 1 (bajo) a 5 (máximo). Prioridad = probabilidad x impacto, ajustada por exposición legal/reputacional.

| ID | Riesgo | P | I | Severidad | Evidencia/estado | Propietario | Tratamiento | Criterio de cierre |
|---|---|---:|---:|---|---|---|---|---|
| R-001 | Posible PII o material sensible en repositorio público | 4 | 5 | P0 | 210 correos y 3 patrones sensibles sin clasificar | Seguridad + Privacidad | Triage, retirada autorizada, rotación si aplica, historial evaluado | 100% clasificado y Secret Guard operativo |
| R-002 | Pérdida simultánea de DB y backups por fallo de disco | 3 | 5 | P0 | Backups visibles en el mismo `/data`; no off-site probado | DB + Operaciones | Backup cifrado fuera del proveedor y restore drill | RPO/RTO medidos y restauración aprobada |
| R-003 | Secret Guard no ejecutable | 5 | 4 | P1 | `ModuleNotFoundError` reproducido | Seguridad + CI | Reparar import sin desactivar control | Gate verde con test positivo/negativo |
| R-004 | Webhook Telegram falsificable | 3 | 4 | P1 | POST no autenticado aceptado localmente | Telegram + Seguridad | Validar secret header y rate limit | Falso webhook 403; real dry-run válido |
| R-005 | Secreto de automatización filtrado por URL | 3 | 4 | P1 | Query/form/JSON aceptados y documentados | Backend + Seguridad | Solo header; deprecar query | Query 403, header autorizado pasa |
| R-006 | Sesión robable o cruzada por cookie débil | 3 | 4 | P1 | `Secure=false`, `SameSite` ausente local | Backend + Seguridad | Configuración segura por entorno | Cookie Secure/HttpOnly/SameSite verificada en Render |
| R-007 | Producción actual no observable/certificada | 4 | 4 | P1 | Render inaccesible desde auditoría, sin APM/pager probado | DevOps + Operaciones | Synthetic monitor y dashboard externo | Runtime/SHA/5xx/latencia con alertas |
| R-008 | Pagos o membresías incorrectos | 3 | 5 | P1 | Stripe real no certificado; ELITE+ no independiente | Pagos + Producto | Certificación test/live no destructiva | Matriz FREE/PRO/ELITE completa y webhook probado |
| R-009 | Incumplimiento legal/comercial | 4 | 4 | P1 | Textos indican revisión pendiente; identidad legal incompleta | Dirección + Legal | Revisión profesional y publicación | Legal owner/jurisdicción/privacidad aprobados |
| R-010 | Restore administrativo causa pérdida de datos | 2 | 5 | P1 | Operación crítica sin doble control demostrado | DB + Seguridad | Reauth, doble confirmación, integridad y audit log | Restore drill controlado y rollback probado |
| R-011 | Datos deportivos stale/falsos en producción | 3 | 5 | P1 | Lógica local fuerte; frescura real no probada | Datos deportivos | SLO de frescura y alerta externa | 7 días de evidencia sin stale público |
| R-012 | Pipeline oficial diverge de cambios candidatos | 4 | 3 | P1 | PR #1/#2 abiertos; `main` en SHA anterior | Release + GitHub | Resolver gates e integrar trazablemente | Main/Render mismo SHA y checks verdes |
| R-013 | Conexiones SQLite no cerradas | 4 | 3 | P2 | Data Vault reproduce `WinError 32` | Backend + DB | Context manager que cierre y test de locks | 100 ciclos sin handle abierto |
| R-014 | Escalabilidad limitada por SQLite/un worker | 4 | 4 | P2 | Gunicorn 1 worker, DB local | Arquitectura | Medir carga; roadmap de Postgres/cola | Prueba de carga con SLO y decisión documentada |
| R-015 | Rendimiento deportivo lento | 4 | 3 | P2 | Evidencia histórica 4.8-5.9 s | Performance | Profiling SQL/cache/Jinja en producción | p95 <2 s en rutas objetivo |
| R-016 | Código monolítico difícil de cambiar | 5 | 3 | P2 | `app.py` ~1.2 MB | Arquitectura | Extracción incremental por dominios | Menor tiempo de test y ownership claro |
| R-017 | Repositorio sobredimensionado | 5 | 3 | P2 | 8,850 archivos; 2,017 de `.venv`; reportes ~1.6 GB | GitHub + Release | Limpiar solo tras inventario y backup | Repo clonado rápido, runtime intacto |
| R-018 | Saturación de logs/auditoría en SQLite | 3 | 3 | P2 | Rate limit y eventos escriben en DB | Operaciones | Retención, rotación y exportación segura | Tamaño/latencia estables 30 días |
| R-019 | Duplicidad de ruta admin | 5 | 2 | P2 | `/admin/client-screens` duplicada | Backend + QA | Unificar regla con test | Una sola regla exacta |
| R-020 | Tests no reproducibles | 4 | 3 | P2 | `pytest` ausente y red restringida | QA + Release | Entorno hermético/lock de dependencias | CI y local ejecutan mismo set |
| R-021 | Cron parcial o invisible | 4 | 3 | P2 | Solo sports cron en `render.yaml` | Automation + DevOps | Registro de ticks y SLO | Último/próximo/resultado visibles y alertados |
| R-022 | Telegram duplica/envía destino erróneo | 2 | 4 | P2 | Dedupe existe, producción no certificada | Telegram | Dry-run, allowlist, daily cap, kill switch | 7 días de delivery audit sin duplicados |
| R-023 | MRR y precios inconsistentes | 4 | 3 | P2 | Admin 19/49 vs cliente 9.99/24.99 | Producto + Finanzas | Fuente única de catálogo | Un catálogo y MRR calculado de Stripe |
| R-024 | Derechos de privacidad no operables | 3 | 4 | P2 | No se encontró flujo de eliminación/exportación de usuario | Privacidad + Soporte | Runbook DSAR y controles | Solicitud de prueba completada y auditada |
| R-025 | Exposición de internals por runtime | 4 | 2 | P2 | Path, ejecutable y flags técnicos públicos | Seguridad + Backend | Vista pública mínima, detalle admin | Endpoint público sin paths/IDs sensibles |
| R-026 | GET con efecto lateral | 3 | 3 | P2 | `/telegram/regenerar-codigo` muta DB | Backend + Seguridad | POST + CSRF + confirmación | GET read-only; test de método |
| R-027 | Sin CSP/HSTS de aplicación | 3 | 3 | P2 | Cabeceras no observadas localmente | Seguridad + DevOps | Política gradual y verificación Render | Headers efectivos sin romper assets |
| R-028 | Proveedor cambia API o agota créditos | 4 | 3 | P2 | Dependencia externa y guards parciales | Datos + Finanzas | Contract tests, budget y backoff | Alerta antes del 80%, fallback probado |
| R-029 | Dependencia de una sola persona | 5 | 4 | P1 | Operación, release e incidentes centralizados | Dirección | Runbooks, acceso de emergencia y sustituto | Simulacro sin propietario principal |
| R-030 | Promesa comercial mayor que evidencia | 3 | 4 | P1 | Visual premium, datos/pagos/operación no certificados | Comercial + Trust | Claim review y beta limitada | Claims ligados a métricas verificadas |
| R-031 | Tabs móviles parcialmente cortados | 4 | 2 | P3 | Muestra visual Live/admin depende de scroll horizontal | Mobile + UX | Indicador de scroll o ajuste de prioridad | 5 viewports sin acción oculta |
| R-032 | Mensaje de ausencia repetitivo | 4 | 1 | P3 | Banner, KPI y panel reiteran el mismo estado | Product + UX | Consolidar jerarquía sin ocultar transparencia | Prueba de comprensión con usuarios |
| R-033 | Hero desplaza valor útil en desktop | 3 | 2 | P3 | App/login usan gran altura inicial | UX | Reducir solo con evidencia above-the-fold | Acción primaria y valor visibles a 768 px |
| R-034 | CTA móvil envuelve texto | 3 | 1 | P3 | Botones como “Preparar Telegram” usan dos líneas | Mobile + UI | Copy corto o ancho estable | 360-430 px sin cambio de layout |
| R-035 | Cobertura limitada de dispositivos reales | 4 | 2 | P4 | Capturas Playwright, no device lab | QA | Matriz mínima iOS/Android | Teclado, safe-area y orientación probados |
| R-036 | Sin ejercicios de caos/DR programados | 4 | 3 | P4 | Runbooks sin simulacro periódico | Ops | Game day trimestral no destructivo | Evidencia de detección y RTO |
| R-037 | Claims comerciales sin revisión periódica | 3 | 3 | P4 | Copy responsable, métricas dinámicas | Trust + Legal | Gate trimestral de claims | Todo claim enlazado a definición/evidencia |

## Concentración de riesgo

- **Personas:** bus factor 1.
- **Datos:** un disco y SQLite.
- **Proveedor:** Render como ejecución y GitHub como fuente única.
- **Controles:** muchos checks internos, poca observabilidad externa.
- **Comercial:** catálogo y legal no cerrados.

## Apetito recomendado

- Cero tolerancia: pérdida de datos, cobros incorrectos, secretos, PII, datos deportivos falsos.
- Tolerancia baja: indisponibilidad, stale, membresía incorrecta, Telegram duplicado.
- Tolerancia moderada: degradación visual menor, proveedor sin datos con fallback honesto.
