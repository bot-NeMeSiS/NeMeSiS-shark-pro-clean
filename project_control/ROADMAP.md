# Roadmap

## Consolidación hacia V1000 · 2026-10-22

Dirección confirmada por el propietario: orientar el trabajo hasta V1000 a consolidar
la plataforma, tomando V977 como referencia de planificación. La prioridad es
estabilidad, usabilidad, operación y aprendizaje con usuarios. Los rangos siguientes
son orientativos y dependen de evidencia; no son fechas ni promesas de éxito comercial.
Se mantiene la [estrategia de concentrar valor](../PRODUCT_STRATEGY.md) y el orden
DEPORTE PRIMERO -> SHARK DESPUÉS -> APUESTAS EN TERCER LUGAR.

### Primer trabajo activo

**Administración en PC:** corregir los defectos reproducibles detectados y comprobar
los recorridos con sesión autenticada, acciones visibles, permisos y resultados
coherentes. Conservar regresiones y revisar móvil para evitar efectos secundarios.
Estado: **EN CURSO**; esta nota no declara el arreglo desplegado. El cierre requiere
evidencia del candidato, sus controles y la revisión posterior del SHA servido.
El [gate público existente](../tools/run_production_quality_browser_gate.py) deja
la revisión de administración autenticada pendiente: una redirección correcta al
login no certifica el funcionamiento del panel.

### V979 candidato local — calendario y etiquetas geográficas · 22 octubre

Basado en V978 (`30f638d262bb89d45cfb2aa38cd98bf6988a19b5`) en el worktree
`codex/v979-country-labels`. Localiza etiquetas de países conocidos en Inicio,
Calendario y el directorio de competiciones sin alterar valores de filtro ni datos
de proveedor. Las tarjetas conservan la hora de inicio ante marcadores vacíos y
mantienen visibles los ceros y resultados parciales, incluso en actualización en
vivo. Incluye una espera determinista de liberación del bloqueo de backup en una
prueba Windows; no modifica el backup de producción.

Regresión local delimitada: 108 PASS y 1 SKIP (enlace simbólico no disponible en
Windows); `py_compile`, `node --check` y `git diff --check` PASS. El árbol aún no
ha pasado la suite completa ni los workflows remotos. Integración y comprobación
de auto despliegue quedan pendientes de esos gates; V979 todavía no está publicada.

### Base existente que se reutiliza

- Calendario, Directo y Centro de Partido, con [frescura de estadísticas](../RELEASE_NOTES_V970_LIVE_STAT_FRESHNESS.md)
  y [relojes propios por valor](../RELEASE_NOTES_V975_MATCH_STATISTICS_CAPTURE_CLOCKS.md).
  Las [cuotas API-Football 1X2 prepartido](../engines/api_football_odds_engine.py)
  ya tienen adaptador; su existencia no demuestra cobertura ni disponibilidad actuales.
- [Beta y feedback](../engines/beta_program_engine.py), programa FIRST_10_USERS,
  [analítica](../engines/product_analytics_engine.py) y
  [Growth/Revenue](../engines/growth_revenue_os_engine.py).
- Cuenta, membresías y [circuito Stripe](../engines/stripe_payments_engine.py).
  Conservar catálogo y permisos existentes; acceso manual y pago confirmado son distintos.
- [Cron maestro](../tools/render_cron_master_tick.py),
  [backup](../tools/render_cron_data_backup.py), controles de consumo y QA existentes.
  Completar los recorridos y su evidencia antes de crear centros o automatizaciones paralelos.

### Fases y criterios de cierre

| Versiones propuestas | Resultado | Criterio de cierre verificable |
|---|---|---|
| V978–V981 | Estabilidad y uso diario | Fallos reproducidos de admin corregidos con regresión; recorridos críticos de cliente/admin comprobados en PC y móvil, incluidos permisos, vacío y error. Sin bloqueos reproducibles abiertos en el alcance acordado. Referencia de rendimiento documentada con carga, entorno y tamaño de muestra. |
| V982–V986 | Datos y continuidad operativa | Fuente, antigüedad y estados coherentes en las superficies revisadas. Evidencia del Cron y sus tareas, restauración aislada con integridad y tiempos registrados, y cierre de los gates externos pertinentes de LRM-001, incluidos Telegram controlado y Stripe test autorizados. |
| V987–V991 | Beta real y medición | Participantes consentidos del programa existente completan el recorrido hasta primer valor. Activación y retorno tienen definición, ventana, denominador y exclusión de cuentas de prueba. Feedback reproducible convertido en arreglos y comprobación posterior; resultados publicados con muestra y límites. |
| V992–V996 | Servicio comercial sostenible | Ciclo de compra, renovación, fallo y cancelación comprobado en el entorno autorizado; pruebas completadas antes de cobros reales. Ingresos, concesiones y estimaciones separados. Costes registrados con fuente y periodo; soporte y decisiones comerciales con responsable. |
| V997–V1000 | Revisión de consolidación | Evidencia conjunta del periodo observado: estabilidad, rendimiento, datos, recuperación, incidencias, beta y cohortes maduras. Si existe venta real, revisar renovaciones y coste efectivo. Decisión documentada sobre alcance consolidado, pendientes y condiciones para ampliar uso. |

### Pendientes NO_VERIFICADOS en esta planificación

- Usuarios activos reales, activación, retención, disposición a pagar y conversión:
  leer código o contar eventos no certifica personas ni cohortes.
- Cobros y renovaciones externos, ingresos confirmados, costes totales y margen:
  requieren registros válidos; ausencia de evidencia no significa cero.
- Recuperación y rendimiento sostenidos, cobertura contratada, entregas externas y
  revisión de los recorridos autenticados: requieren evidencia actual y delimitada.
- Derechos, condiciones comerciales y decisiones de privacidad: requieren revisión
  pertinente y decisión del propietario; el código no acredita su cumplimiento.

Estos pendientes expresan límites de esta revisión, no inexistencia de capacidades.
Los objetivos cuantitativos se fijan a partir de una referencia medida; no se inventan
porcentajes para cerrar una fase. La implementación, instrumentación y QA pueden
avanzar técnicamente; validar utilidad, retorno y venta requiere usuarios reales,
tiempo y decisiones del propietario. Los envíos, cobros y activaciones externas se
rigen por la autorización concreta vigente.

Las versiones no sustituyen usuarios, cohortes ni ciclos de renovación. Llegar a V1000
no cierra [LRM-001](../NEMESIS_LIVING_ROADMAP.md) por numeración: sus gates se resuelven
con evidencia. Reconciliar cada estado con código y operación actuales, conservando
la historia sin copiar sus etiquetas como estado vigente.

## Historial preservado · 2026-09-19

El contenido siguiente conserva la planificación fechada original y sus dependencias.

Estrategia de consulta. Estados actuales exclusivamente en [CODEX_QUEUE](CODEX_QUEUE.md),
no en este resumen ni en chats antiguos. Reconciliado 2026-09-19.
La [vision](../NEMESIS_MASTER_VISION.md), el [Living Roadmap historico](../NEMESIS_LIVING_ROADMAP.md)
y las [reglas X congeladas](../NEMESIS_X_IMPLEMENTATION_RULES.md) conservan sus ideas,
contratos y gates. No se declara LRM-001 terminado ni se autoriza NeMeSiS X.

## FIRST 10: secuencia por evidencia

| Orden | Incremento | Ya existe | Falta / gate |
|---|---|---|---|
| 1 | CX-SE-01 | Lectura read-only, stale honesto, historia nullable, procedencia | DONE LOCAL; no publicar sin autorizacion; 12 QA globales no certificados |
| 2 | CX-ORG-01 | Control, indice de continuidad, cola unica e inventario sin retirada | Revisar dependencias y UNKNOWN; no limpiar funcionalidad |
| 3 | CX-RESULTS-01 | Calendario/Partidos, fechas, Match Center y Directo PR14 adaptado localmente | Historico, cobertura y paginacion completos pendientes; no confundir local con produccion |
| 4 | CX-DATA-01 | Gateway/adaptadores/almacenes existentes | Fuente permitida, muestra real, identidad/procedencia/frescura; coste/cuota conocidos |
| 5 | CX-INTELLIGENCE/SHARK | Match Context, resumen factual y capas SHARK | Una capacidad delimitada con hechos suficientes, no simulacion de IA activa |
| 6 | CX-MEDIA | Rights fail-closed | Prueba de derechos y cobertura; no comprar/descargar/rehostear por defecto |
| 7 | CX-PLANS/ANALYTICS | Membresias, Growth, Revenue | Permisos y metricas reales; preservar tiers/precios; no inventar MRR/ROI |
| 8 | CX-STRIPE | Rutas/fundacion de pagos existentes | Encargo separado de test, aprobacion; ningun cobro real aqui |
| 9 | CX-FIRST10 | LRM-001/beta como estrategia | Release autorizado, checks, soporte, privacidad, operacion y consentimiento |

## Condiciones de lanzamiento

- Produccion y GitHub verificados por SHA, no version nominal; Sentinel del SHA efectivo.
- Autorizacion de rama + PR + checks, sin excepciones de proteccion ni force.
- P0/P1 corregibles recertificados; positivos ambientales pendientes no convertidos en PASS.
- Datos reales y limitaciones claras; LIVE importante sin evidencia independiente no certificado.
- Auth cliente/admin, soporte, privacidad y rutas de cuenta verificadas en el entorno pertinente.
- Aprobacion humana visual pendiente y permisos comerciales explicitos.
- Costes reales conocidos cuando haya presupuesto; no inferir cero desde ausencia de compras.

## No hacer para adelantar FIRST 10

No esperar toda la historia del futbol, abrir proveedor nuevo por cuota agotada,
descomponer app.py, purgar CSS/tests historicos, activar reparador autonomo,
construir otro scheduler o duplicar centros deportivos ya presentes.

Cada incremento requiere problema, consumidor actual, evidencia, dependencia,
aceptacion, presupuesto/permiso y prueba reversible antes de editar.
