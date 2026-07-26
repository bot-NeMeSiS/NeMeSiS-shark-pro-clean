# Sports Core - Match Intelligence Engine

## Decisión ejecutiva

**GATE LOCAL: PASS**

NeMeSiS dispone de un único motor reutilizable de inteligencia de partido:
`MATCH-INTELLIGENCE-EVIDENCE-V1`.

El motor transforma hechos deportivos ya disponibles en contexto estructurado y
explicable. No consulta proveedores, no escribe en la base de datos, no envía
Telegram, no invoca IA generativa, no calcula probabilidades de apuesta y no
inventa información ausente.

Producción no se ha modificado ni certificado durante este sprint.

## Base y alcance

- Rama: `main`
- Commit base: `5b3ab67c88503528d6cabe4a361bb94a07c09c39`
- Runtime preservado:
  `V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL`
- Nueva versión funcional: no
- Commit, push y deploy: no realizados
- Llamadas deportivas externas durante QA: `0`
- Envíos Telegram: `0`
- Acciones de pago: `0`

La implementación amplía el módulo histórico Match Intelligence existente. No
crea una arquitectura paralela y mantiene MatchContext y los componentes
canónicos del Match Center como base aprobada.

## Arquitectura canónica

Flujo único:

`hechos reales guardados`
-> `MatchContext`
-> `MATCH-INTELLIGENCE-EVIDENCE-V1`
-> `vista de consumidor read-only`
-> `Match Center / SHARK / contrato Telegram`

El motor recibe únicamente datos entregados por el consumidor:

- identidad, estado y marcador;
- ciclo de vida y minuto canónicos;
- eventos confirmados de la cronología;
- estadísticas frescas del proveedor;
- competición;
- hechos del tracker local;
- picks relacionados ya disponibles;
- histórico comparable opcional.

El motor no realiza I/O. MatchContext construye una única instantánea y SHARK
consume exactamente ese mismo objeto. Ningún consumidor necesita recalcular la
interpretación deportiva por su cuenta.

## Contrato estructurado

La salida canónica contiene:

1. `estado_partido`
2. `ritmo`
3. `presion`
4. `dominador`
5. `equilibrio`
6. `fase`
7. `riesgo`
8. `eventos_clave`
9. `tendencias`
10. `cambios_recientes`

Cada conclusión incluye:

- estado de certificación;
- valor estructurado;
- identificadores de evidencia;
- datos de soporte;
- información ausente;
- método determinista;
- limitaciones.

Estados permitidos:

- `VERIFIED`
- `PARTIALLY_VERIFIED`
- `NOT_CERTIFIED`
- `STALE`
- `INSUFFICIENT_DATA`
- `REQUIRES_REVIEW`

Los estados técnicos permanecen disponibles para admin y APIs. El cliente ve
etiquetas claras en español y no recibe tokens internos.

## Reglas de evidencia

- Estado y marcador son hechos directos cuando están confirmados.
- Presión y dominador reutilizan lecturas derivadas de estadísticas reales del
  proveedor; nunca se presentan como probabilidad.
- Riesgo representa solo incidencias observadas, como roja, penalti, VAR o
  interrupción. No es riesgo financiero, de apuesta, lesión o resultado.
- Los cambios recientes usan una ventana fija de 15 minutos.
- Una única instantánea nunca se convierte en tendencia.
- Datos stale no pueden activar una interpretación SHARK.
- La ausencia de datos genera limitaciones o `INSUFFICIENT_DATA`.
- No se inventa una puntuación numérica de confianza.
- Un estado live genérico usa el minuto confirmado para distinguir primera y
  segunda parte. Sin minuto suficiente, la fase queda sin especificar.

## Consumidores

### Integrados ahora

- **Match Center:** recibe la instantánea canónica desde MatchContext.
- **Panel SHARK del partido:** muestra solo lecturas soportadas por la misma
  evidencia.
- **Contexto SHARK de partido seleccionado:** recibe el mismo envelope y no
  reconstruye contexto.
- **Asistente de producto SHARK:** explica la evidencia de forma determinista y
  sin llamada generativa.
- **Telegram Intelligence:** recibe el contrato read-only para una integración
  futura. No se implementó ni envió ningún mensaje nuevo.
- **Developer Center y Company Board:** reflejan la capacidad integrada desde
  el registro y roadmap compartidos.
- **Superficie histórica V745:** conserva compatibilidad mediante una vista
  determinista respaldada por el motor canónico.

### Preparados, no implementados

- Team Center
- Competition Center
- Player Center
- Sports Graph

Sus contratos de consumidor y referencias de entidades quedan preparados. No
se añadieron rutas, pantallas, esquemas ni escrituras de grafo. Las escrituras
Sports Graph permanecen expresamente desautorizadas.

## Mejora para el usuario

El usuario puede comprender desde una única lectura coherente:

- fase y marcador confirmados;
- actividad observada;
- presión y dominio respaldados cuando existen estadísticas;
- incidencias que cambian el contexto;
- cambios recientes confirmados;
- evidencia que sostiene cada lectura;
- información ausente o desactualizada.

La mejora visible es la coherencia entre Match Center y SHARK. La mejora
invisible es que los futuros consumidores pueden reutilizar una instantánea
pura sin nuevas consultas, llamadas de proveedor o ramas interpretativas.

## Deuda técnica eliminada

- Eliminada la interpretación SHARK duplicada dentro de MatchContext.
- Consolidado el módulo histórico dentro del núcleo Sports Core.
- Sustituido el contexto libre por vistas estructuradas read-only.
- Unificado el contrato de explicabilidad.
- Añadidos diagnósticos explícitos de cero I/O, cero IA generativa y cero
  acciones automáticas.
- Conservados contratos, rutas y campos legacy vigentes.

## Rendimiento

### Motor puro

Medición sobre 5.000 construcciones representativas:

- mediana: `0.1794 ms`
- p95: `0.3579 ms`
- mínimo: `0.1667 ms`
- máximo: `1.0545 ms`

### Ruta Match Center

Medición sobre 30 cargas locales con DB temporal aislada:

- primera carga: `380.51 ms`
- mediana caliente: `23.08 ms`
- p95: `59.15 ms`
- mínimo: `15.11 ms`
- máximo: `380.51 ms`
- respuesta: `46.579 bytes`
- respuestas distintas de HTTP 200: `0`

El SHA-256 de la base temporal fue idéntico antes y después de los 30 GET.

## Browser QA

Escenarios completo e incompleto:

- desktop `1366x768`;
- tablet `834x1194`;
- móvil `390x844`.

Resultado: **PASS, 6/6**

Confirmado:

- HTTP 200;
- overflow horizontal: 0;
- CLS: 0;
- errores de consola, página y 5xx: 0;
- llamadas externas y a proveedores: 0;
- textos cortados: 0;
- literales inseguros: 0;
- estados técnicos visibles: 0;
- mojibake visible: 0;
- 10 componentes canónicos únicos;
- navegación cliente/admin no duplicada;
- escenario completo con 4 eventos, 4 estadísticas reales y SHARK explicable;
- escenario parcial sin estadísticas o SHARK inventados y con fallbacks seguros.

Las seis capturas PNG se decodificaron, conservaron sus dimensiones responsive
y superaron la comprobación de integridad de píxeles no vacíos.

## QA automatizado

- `py_compile`: PASS
- `compileall`: PASS
- pytest completo: `99/99` PASS
- suite focalizada Match Intelligence y foundation: `27/27` PASS
- integridad Jinja: PASS
- contrato Calendar V940: PASS
- contrato Match Center V944: PASS
- contrato Live Story: PASS
- Madrid Time verano/invierno: PASS
- importación y rutas: PASS, 658 rutas
- auditoría: 707 rutas y 956 enlaces
- enlaces rotos: 0
- bucles de redirect: 0
- Continuous Sentinel: `10/10`
- incidencias abiertas o críticas: 0
- Privacy/Secret Guard: PASS
- archivos analizados: 1.004
- secretos confirmados: 0
- hallazgos de privacidad: 0

## Sentinel y AutoPilot

Sentinel valida:

- marcador del contrato canónico;
- constructor único;
- adaptador de vistas;
- integración SHARK y Telegram;
- cero consultas y escrituras del motor;
- cero llamadas externas y generativas;
- ausencia de confianza numérica inventada;
- escrituras Sports Graph desactivadas.

Un test de mutación cambia el marcador contractual y demuestra que Sentinel:

- detecta la regresión;
- reduce la salud;
- abre incidencia P1;
- genera una tarea AutoPilot específica;
- exige aprobación humana;
- no edita, commitea, publica ni despliega automáticamente.

## Seguridad

El motor importa únicamente `typing` y no tiene acceso a:

- SQLite;
- clientes HTTP;
- credenciales de proveedor;
- envío Telegram;
- Stripe;
- OpenAI u otro modelo generativo;
- persistencia de archivos.

Los diagnósticos confirman cero consultas DB, escrituras DB, llamadas externas,
envíos Telegram, llamadas generativas y acciones automáticas.

## Limitaciones y áreas no certificadas

- Browser QA usa fixtures aislados y claramente separados de producción.
- La frescura real del proveedor en Render no se ha certificado.
- Telegram queda integrado por contrato, sin mensaje real.
- Team Center, Competition Center, Player Center y Sports Graph no están
  implementados.
- Presión y dominador siguen siendo interpretaciones parcialmente verificadas
  de estadísticas reales.
- Tendencias requieren instantáneas históricas comparables.
- Runtime, latencia y logs de producción permanecen sin modificar ni certificar.
- La visualización manual directa de PNG quedó bloqueada por ACL de Windows;
  DOM, layout, consola, red, decodificación e integridad de píxeles sí fueron
  validados.

## Estado final

**MATCH INTELLIGENCE ENGINE: READY LOCALLY**

El Sports Core dispone de un núcleo único, explicable, rápido y seguro por
defecto. Mejora Match Center y SHARK, elimina cálculos duplicados y prepara la
integración futura de Team Center, Competition Center, Player Center y Sports
Graph sin implementarlos antes de tiempo.

La siguiente acción autorizable es la revisión humana del diff local. La
certificación de producción requiere una decisión explícita de commit, push y
deploy.
