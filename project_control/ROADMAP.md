# Roadmap

Prioridad operativa aqui y en [CODEX_QUEUE](CODEX_QUEUE.md), no en chats antiguos.
La [vision](../NEMESIS_MASTER_VISION.md), el [Living Roadmap historico](../NEMESIS_LIVING_ROADMAP.md)
y las [reglas X congeladas](../NEMESIS_X_IMPLEMENTATION_RULES.md) conservan sus ideas,
contratos y gates. No se declara LRM-001 terminado ni se autoriza NeMeSiS X.

## FIRST 10: secuencia por evidencia

| Orden | Incremento | Ya existe | Falta / gate |
|---|---|---|---|
| 1 | CX-SE-01 | Lectura read-only, stale honesto, historia nullable, procedencia | DONE LOCAL; no publicar sin autorizacion; 12 QA globales no certificados |
| 2 | CX-ORG-01 | Control, mapa, cola y retirada solo regenerable | Revision del cierre y alcance truncado; no limpiar funcionalidad |
| 3 | CX-RESULTS-01 | Calendario/Partidos, fechas, estado canonico, Match Center | Validar ayer/otra fecha/final/0-0/ausencia/paginacion/volver sin pick; no iniciado |
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
