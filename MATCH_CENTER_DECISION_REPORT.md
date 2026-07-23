# Match Center Decision Report

## 0. Control del documento

**Sprint estratégico:** `V943_MATCH_CENTER_DECISION_BOARD_FINAL`  
**Estado:** `MATCH_CENTER_ARCHITECTURE_APPROVED / IMPLEMENTATION_READY`  
**Naturaleza:** decisión documental  
**Código autorizado en este Sprint:** no  
**Producción modificada:** no  
**Implementación ejecutada:** no  

Entradas normativas:

- `NEMESIS_PRODUCT_BIBLE.md`
- `NEMESIS_SPORTS_UX_BIBLE.md`
- `NEMESIS_MATCH_CENTER_UX_BIBLE.md`

Este documento selecciona la arquitectura funcional de Match Center. No autoriza todavía código, HTML, CSS, Python, rutas, cambios de datos, push o deploy.

---

# 1. Decisión ejecutiva

## Arquitectura principal aprobada

**Alternativa D: Historia viva por ciclo**

Puntuación ponderada:

**93,2/100**

La decisión no se basa en preferencia visual. D obtiene la mejor evaluación porque:

- conserva una identidad estable antes, durante y después;
- reduce carga cognitiva mediante prioridad por fase;
- permite visitas rápidas y exploración profunda;
- funciona en desktop y móvil con la misma verdad;
- integra SHARK y Telegram de forma contextual;
- se conecta naturalmente con el Sports Entity Model;
- degrada con honestidad cuando faltan datos;
- cumple mejor la Product Bible;
- mantiene el partido como experiencia deportiva, no como oportunidad de apuesta.

## Elementos subordinados aprobados

D se completa con elementos concretos de otras alternativas:

- **B, Línea temporal total:** su cronología se incorpora como módulo canónico de hechos y cambios.
- **A, Dossier deportivo:** su organización temática se utiliza para la profundidad estable de estadísticas, participantes y contexto.
- **E, Profundidad bajo demanda:** su progresión se utiliza para revelar detalle sin crear un segundo producto o modo.
- **C, Sala de decisión responsable:** su gramática de evidencia, riesgos e invalidadores se limita a SHARK, picks y Bankroll.

La combinación no cambia la arquitectura principal. Cada elemento subordinado tiene un hogar y un límite.

---

# 2. Reglas de la decisión

## 2.1 Restricciones no negociables

La arquitectura debe:

- usar datos reales;
- conservar lifecycle y frescura;
- mantener hechos básicos útiles en FREE;
- separar hecho, contexto, cambio, criterio y acción;
- funcionar sin SHARK, pick o Telegram;
- mostrar estados seguros;
- respetar juego responsable;
- preservar contexto al entrar y salir;
- ser auditable;
- ser compatible con Browser QA y Sentinel;
- reutilizar componentes existentes cuando cumplan el contrato.

## 2.2 Vetos

Una alternativa no puede ganar si:

- reduce el partido a una apuesta;
- necesita datos no certificables para funcionar;
- presenta stale como live;
- obliga a reaprender la experiencia en cada fase;
- crea dos verdades entre móvil y desktop;
- depende de personalización opaca;
- no puede operar con cobertura parcial;
- dificulta acceso o tecnologías de asistencia;
- impide investigar una corrección.

## 2.3 Independencia de la evaluación

`NEMESIS_SPORTS_UX_BIBLE.md` ya identificaba D como dirección estratégica. Esa decisión previa no recibe puntos adicionales.

La puntuación V943 se calcula exclusivamente a partir de los criterios y pesos documentados en este informe.

---

# 3. Método de puntuación

## 3.1 Escala

Cada alternativa se puntúa de 1 a 5.

| Puntuación | Definición |
|---:|---|
| 5 | Cumple el criterio de forma excelente y con riesgos controlables |
| 4 | Cumple bien; requiere mitigaciones conocidas |
| 3 | Viable; presenta compromisos materiales |
| 2 | Débil; depende de cambios o mitigaciones importantes |
| 1 | Contradice el criterio o no puede sostenerlo |

En mantenimiento y riesgo técnico, una puntuación mayor significa:

- mantenimiento más sencillo;
- riesgo más controlable.

## 3.2 Pesos

| Criterio | Peso | Motivo |
|---|---:|---|
| Experiencia de usuario | 13 | Es la finalidad primaria |
| Tiempo para encontrar información | 10 | Match Center debe resolver preguntas rápidamente |
| Carga cognitiva | 10 | La profundidad no puede convertirse en saturación |
| Escalabilidad | 8 | Debe funcionar con cobertura y fases crecientes |
| Rendimiento | 7 | El estado principal no puede depender de módulos secundarios |
| Desktop | 5 | Debe permitir profundidad y comparación |
| Mobile | 7 | Móvil es una experiencia primaria |
| Accesibilidad | 7 | Es parte del concepto, no una corrección posterior |
| Integración SHARK | 7 | Es una diferencia propia del producto |
| Integración Telegram | 5 | Debe extender la continuidad |
| Sports Entity Model | 6 | Partido, equipos, competición y jugadores deben conectarse |
| Mantenimiento | 5 | La empresa debe poder evolucionar la experiencia |
| Riesgo técnico controlable | 5 | Lifecycle, live y datos parciales son críticos |
| Coherencia con Product Bible | 5 | Ninguna alternativa puede contradecir la fundación |
| **Total** | **100** | |

## 3.3 Fórmula

```text
TOTAL BRUTO = suma(puntuación × peso)
MÁXIMO = 500
TOTAL NORMALIZADO = total bruto / 5
```

---

# 4. Resultado comparativo

## 4.1 Matriz de puntuaciones

| Criterio | Peso | A Dossier | B Cronología | C Decisión | D Historia por ciclo | E Profundidad |
|---|---:|---:|---:|---:|---:|---:|
| Experiencia de usuario | 13 | 3 | 4 | 3 | 5 | 4 |
| Tiempo para encontrar | 10 | 4 | 3 | 4 | 5 | 4 |
| Carga cognitiva | 10 | 3 | 3 | 4 | 5 | 5 |
| Escalabilidad | 8 | 4 | 3 | 3 | 5 | 4 |
| Rendimiento | 7 | 3 | 3 | 4 | 4 | 4 |
| Desktop | 5 | 5 | 3 | 5 | 5 | 4 |
| Mobile | 7 | 3 | 5 | 4 | 5 | 5 |
| Accesibilidad | 7 | 4 | 3 | 4 | 4 | 4 |
| SHARK | 7 | 3 | 5 | 5 | 5 | 4 |
| Telegram | 5 | 4 | 5 | 5 | 5 | 4 |
| Sports Entity Model | 6 | 5 | 3 | 3 | 5 | 4 |
| Mantenimiento | 5 | 4 | 3 | 3 | 3 | 2 |
| Riesgo técnico controlable | 5 | 4 | 3 | 2 | 3 | 3 |
| Product Bible | 5 | 4 | 4 | 2 | 5 | 4 |

## 4.2 Totales

| Posición | Alternativa | Total bruto | Total normalizado | Estado |
|---:|---|---:|---:|---|
| 1 | D Historia viva por ciclo | 466/500 | **93,2/100** | APROBADA COMO PRINCIPAL |
| 2 | E Profundidad bajo demanda | 402/500 | **80,4/100** | ELEMENTO SUBORDINADO |
| 3 | A Dossier deportivo | 367/500 | **73,4/100** | ELEMENTO SUBORDINADO |
| 4 | C Sala de decisión responsable | 365/500 | **73,0/100** | USO LIMITADO |
| 5 | B Línea temporal total | 356/500 | **71,2/100** | MÓDULO SUBORDINADO |

La clasificación no implica que B sea inútil. Su cronología aporta un módulo excelente, pero no una arquitectura completa equilibrada.

---

# 5. Justificación completa: Alternativa A

## Dossier deportivo

| Criterio | Nota | Justificación |
|---|---:|---|
| Experiencia de usuario | 3/5 | Ofrece profundidad y previsibilidad, pero obliga al usuario a construir la historia entre secciones |
| Tiempo para encontrar | 4/5 | Los hogares temáticos facilitan encontrar un dato conocido; es más lento para responder “qué cambió” |
| Carga cognitiva | 3/5 | La estructura es comprensible, pero muchos módulos compiten por atención |
| Escalabilidad | 4/5 | Añade fuentes o módulos con relativa facilidad y degrada bien por ausencia |
| Rendimiento | 3/5 | La tentación de cargar el expediente completo aumenta datos, render y longitud |
| Desktop | 5/5 | Aprovecha bien comparación, tablas y profundidad simultánea |
| Mobile | 3/5 | El expediente produce recorridos largos y frecuentes saltos temáticos |
| Accesibilidad | 4/5 | Landmarks y orden estable son favorables, aunque la longitud exige navegación interna robusta |
| SHARK | 3/5 | Dispone de mucha evidencia, pero puede quedar aislado como otra sección |
| Telegram | 4/5 | Permite enlaces precisos a información temática |
| Sports Entity Model | 5/5 | Equipos, competición y jugadores tienen relaciones y hogares claros |
| Mantenimiento | 4/5 | Los límites por módulo son claros; el riesgo es acumulación gradual |
| Riesgo técnico | 4/5 | La arquitectura es predecible y fácil de degradar, con riesgo moderado de duplicación |
| Product Bible | 4/5 | Cumple datos y profundidad, pero reduce continuidad y prioridad de cambios |

## Fortalezas

- auditabilidad;
- hogar estable de cada dato;
- excelente desktop;
- conexión natural de entidades;
- compatibilidad con cobertura parcial.

## Riesgos

- archivo de datos sin narrativa;
- exceso de módulos;
- mayor scroll móvil;
- repetición de estado;
- dificultad para destacar cambios.

## Elemento conservado

La profundidad temática se conserva dentro de D para:

- estadísticas;
- participantes;
- contexto;
- entidades;
- evidencia SHARK.

No se conserva como estructura principal.

---

# 6. Justificación completa: Alternativa B

## Línea temporal total

| Criterio | Nota | Justificación |
|---|---:|---|
| Experiencia de usuario | 4/5 | Cuenta una historia continua y favorece retorno, pero no resuelve igual de bien preguntas temáticas |
| Tiempo para encontrar | 3/5 | El último evento es inmediato; una alineación completa o un dato histórico puede quedar disperso |
| Carga cognitiva | 3/5 | El flujo natural ayuda, pero muchos eventos generan ruido y fatiga |
| Escalabilidad | 3/5 | El volumen de hitos crece con cobertura, correcciones y duración |
| Rendimiento | 3/5 | Las cronologías extensas exigen paginación, agrupación y actualización cuidadosa |
| Desktop | 3/5 | Funciona, pero aprovecha peor comparación y profundidad simultánea |
| Mobile | 5/5 | La lectura secuencial encaja de forma excelente con una pantalla estrecha |
| Accesibilidad | 3/5 | Las actualizaciones dinámicas, live regions y orden corregido requieren especial cuidado |
| SHARK | 5/5 | Puede explicar cómo cambió una hipótesis frente a evidencia nueva |
| Telegram | 5/5 | Cada alerta tiene un hito y destino natural |
| Sports Entity Model | 3/5 | Las entidades aparecen ligadas a eventos, pero pierden un hogar completo |
| Mantenimiento | 3/5 | Dedupe, correcciones, orden y agrupación elevan complejidad |
| Riesgo técnico | 3/5 | Errores de timestamp o proveedor pueden desordenar la historia |
| Product Bible | 4/5 | Encaja con “cambio antes que repetición”, pero puede premiar actividad sobre claridad |

## Fortalezas

- continuidad temporal;
- excelente móvil;
- retorno contextual;
- integración SHARK;
- integración Telegram;
- trazabilidad del cambio.

## Riesgos

- feed infinito;
- eventos de poco valor;
- correcciones difíciles;
- datos estructurales dispersos;
- actualización accesible compleja.

## Elemento conservado

La cronología se conserva como módulo canónico de:

- eventos;
- cambios;
- correcciones;
- hitos SHARK;
- mensajes Telegram relacionados.

No ordena por sí sola todo Match Center.

---

# 7. Justificación completa: Alternativa C

## Sala de decisión responsable

| Criterio | Nota | Justificación |
|---|---:|---|
| Experiencia de usuario | 3/5 | Resuelve muy bien una intención de decisión, pero debilita el seguimiento deportivo universal |
| Tiempo para encontrar | 4/5 | Evidencia, riesgo y pick son rápidos; otros trabajos quedan subordinados |
| Carga cognitiva | 4/5 | La síntesis reduce ruido, aunque escenarios e invalidadores pueden exigir experiencia |
| Escalabilidad | 3/5 | Solo escala donde datos, análisis y gobierno permiten una decisión |
| Rendimiento | 4/5 | Puede priorizar un conjunto acotado de evidencia |
| Desktop | 5/5 | Comparación de razones, riesgos y escenarios funciona muy bien |
| Mobile | 4/5 | La síntesis funciona, pero la evidencia profunda puede fragmentarse |
| Accesibilidad | 4/5 | Tiene jerarquía clara; debe evitar lenguaje y controles dependientes de riesgo o color |
| SHARK | 5/5 | SHARK tiene un propósito central y concreto |
| Telegram | 5/5 | Cambios de decisión o invalidadores producen alertas claras |
| Sports Entity Model | 3/5 | Las entidades se convierten principalmente en evidencia, no en experiencias conectadas |
| Mantenimiento | 3/5 | Reglas, muestras, membresías y explicaciones requieren gobierno permanente |
| Riesgo técnico | 2/5 | Alta dependencia de datos, cuotas, lifecycle y análisis; error con impacto reputacional |
| Product Bible | 2/5 | Riesgo directo de reducir deporte a apuesta y contradecir “NeMeSiS vende criterio” |

## Fortalezas

- claridad de criterio;
- diferenciación premium;
- riesgos visibles;
- invalidadores;
- SHARK y Telegram con propósito.

## Riesgos

- producto centrado en apostar;
- presión comercial;
- dependencia de cobertura;
- riesgo legal y reputacional;
- menor utilidad sin pick.

## Elemento conservado

Su gramática se conserva únicamente dentro de:

- lectura SHARK;
- pick;
- Bankroll;
- revisión de decisión.

Nunca gobierna la arquitectura general del partido.

---

# 8. Justificación completa: Alternativa D

## Historia viva por ciclo

| Criterio | Nota | Justificación |
|---|---:|---|
| Experiencia de usuario | 5/5 | Conserva identidad y adapta prioridad a la necesidad real de cada fase |
| Tiempo para encontrar | 5/5 | El estado y cambio principal aparecen primero; la profundidad mantiene hogares estables |
| Carga cognitiva | 5/5 | Reduce lo visible sin ocultar acceso ni crear modos separados |
| Escalabilidad | 5/5 | Los módulos se activan por lifecycle y disponibilidad usando una misma verdad |
| Rendimiento | 4/5 | Permite priorizar núcleo y diferir profundidad; la orquestación añade coste controlable |
| Desktop | 5/5 | Coordina presente, contexto y profundidad sin perder orientación |
| Mobile | 5/5 | La prioridad secuencial encaja con uso móvil y visitas rápidas |
| Accesibilidad | 4/5 | Puede conservar una estructura semántica estable, pero los cambios de prioridad necesitan control |
| SHARK | 5/5 | SHARK responde a la fase y puede permanecer en silencio |
| Telegram | 5/5 | Cada mensaje devuelve a la misma historia y al cambio correcto |
| Sports Entity Model | 5/5 | Partido, equipos, competición y jugadores forman una red contextual sin duplicar |
| Mantenimiento | 3/5 | Las reglas editoriales y lifecycle son más complejas que un dossier fijo |
| Riesgo técnico | 3/5 | Una fase o frescura incorrecta puede elevar el módulo equivocado; requiere contratos fuertes |
| Product Bible | 5/5 | Cumple continuidad, contexto, una verdad, calidad, serenidad y experiencia antes que funciones |

## Fortalezas

- continuidad;
- orientación;
- velocidad cognitiva;
- utilidad en cualquier fase;
- coherencia móvil/desktop;
- safe mode;
- integración contextual;
- identidad propia.

## Riesgos

- transición de lifecycle incorrecta;
- prioridad inestable;
- reglas editoriales opacas;
- módulos que suben o bajan sin explicación;
- complejidad de QA por estados.

## Mitigaciones obligatorias

- estructura semántica estable;
- contratos de lifecycle y frescura;
- prioridad explicable;
- hogares canónicos;
- estado “qué cambió”;
- Browser QA por fase;
- mutaciones Sentinel;
- fallback seguro.

---

# 9. Justificación completa: Alternativa E

## Lectura esencial y profundidad bajo demanda

| Criterio | Nota | Justificación |
|---|---:|---|
| Experiencia de usuario | 4/5 | Reduce densidad y da control, con riesgo de esconder capacidades |
| Tiempo para encontrar | 4/5 | Lo esencial es rápido; una pregunta profunda puede requerir varias aperturas |
| Carga cognitiva | 5/5 | La progresión evita saturación inicial |
| Escalabilidad | 4/5 | Admite módulos nuevos, pero multiplica decisiones de revelado |
| Rendimiento | 4/5 | Puede cargar solo lo necesario; la memoria de estado añade complejidad |
| Desktop | 4/5 | Funciona bien, aunque puede infrautilizar comparación disponible |
| Mobile | 5/5 | Excelente para lectura progresiva y espacio reducido |
| Accesibilidad | 4/5 | Es viable con controles claros; expansión, foco y estado deben ser rigurosos |
| SHARK | 4/5 | Separa síntesis y evidencia, pero puede quedar oculto |
| Telegram | 4/5 | Puede enlazar a profundidad concreta, con riesgo de contexto cerrado |
| Sports Entity Model | 4/5 | Las entidades pueden revelarse por intención sin perder su identidad |
| Mantenimiento | 2/5 | Descubribilidad, estado, equivalencia y múltiples profundidades aumentan deuda |
| Riesgo técnico | 3/5 | Estado de expansión y retorno puede romper coherencia entre dispositivos |
| Product Bible | 4/5 | Cumple simplicidad con profundidad, pero puede crear dos productos u ocultación |

## Fortalezas

- baja carga inicial;
- excelente móvil;
- rendimiento progresivo;
- control de profundidad;
- flexibilidad.

## Riesgos

- información oculta;
- demasiadas interacciones;
- dos experiencias incoherentes;
- pérdida de estado;
- mantenimiento alto.

## Elemento conservado

Se conserva la revelación progresiva como comportamiento dentro de D.

No se crean:

- modo rápido;
- modo experto;
- dos verdades;
- dos estructuras.

---

# 10. Riesgos de la arquitectura aprobada

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Lifecycle incorrecto eleva contenido equivocado | Media | Alto | Contrato canónico, tests de transición y Sentinel |
| Cambios de prioridad desorientan | Media | Alto | Ancla estable, “qué cambió” y orden semántico |
| Cobertura parcial deja huecos | Alta | Medio | Estados seguros y omisión explicada |
| Dossier subordinado crece sin control | Media | Medio | Hogar único y presupuesto de atención |
| Timeline acumula ruido | Media | Medio | Eventos significativos, dedupe y agrupación |
| SHARK invade el partido | Media | Alto | Entrada por pregunta, silencio permitido |
| Telegram duplica la experiencia | Media | Medio | Motivo, dedupe y retorno contextual |
| Móvil pierde profundidad | Media | Alto | Paridad funcional y Browser QA |
| Desktop se llena por espacio disponible | Media | Medio | Jerarquía por tarea, no por superficie |
| Actualización live afecta accesibilidad | Media | Alto | Live regions controladas y foco estable |
| Membresía crea verdades distintas | Baja | Crítico | Hechos comunes y contratos de acceso |
| Rendimiento depende de módulos secundarios | Media | Alto | Núcleo independiente y carga diferida |

---

# 11. Elementos descartados

## Descartados como arquitectura principal

- dossier universal;
- feed cronológico universal;
- pick como centro;
- dos modos de producto;
- dashboard estático;
- personalización opaca.

## Descartados por completo

- marcador o minuto inventado;
- timeline de relleno;
- estadística sin pregunta;
- alineación probable presentada como oficial;
- CTA Telegram repetido;
- SHARK siempre visible;
- Bankroll sin configuración voluntaria;
- hecho básico bloqueado para convertir;
- estado live sin frescura;
- duplicación de datos entre módulos;
- navegación que pierde Calendario de origen.

---

# 12. Contrato funcional aprobado

## 12.1 Nombre

`MATCH-CENTER-LIFECYCLE-STORY-V1`

## 12.2 Propósito

Mantener una historia única, verificable y responsable del partido durante todo su ciclo.

## 12.3 Invariantes

1. Una identidad estable.
2. Un lifecycle canónico.
3. Un marcador y fase reales.
4. Una señal clara de frescura.
5. Un resumen de qué cambió.
6. Un hogar único por dato.
7. Prioridad por fase, no verdad diferente.
8. Profundidad progresiva sin modos separados.
9. Hechos básicos útiles en FREE.
10. SHARK, picks, Telegram y Bankroll son condicionales.
11. Estado seguro ante ausencia o stale.
12. Contexto de retorno preservado.

## 12.4 Secuencia de experiencia

```text
IDENTIDAD
→ ESTADO ACTUAL
→ QUÉ CAMBIÓ
→ HISTORIA DE LA FASE
→ PROFUNDIDAD TEMÁTICA
→ CRITERIO CONDICIONAL
→ CONTINUIDAD
→ RETORNO
```

## 12.5 Fases

- programado;
- alineaciones pendientes;
- alineaciones confirmadas;
- próximo a comenzar;
- live;
- descanso;
- interrumpido;
- suspendido;
- aplazado;
- finalizado;
- resultado pendiente;
- stale;
- cobertura insuficiente.

## 12.6 Prioridad por fase

| Fase | Prioridad |
|---|---|
| Previa lejana | Identidad, hora, competición y contexto |
| Previa cercana | Alineaciones, ausencias y cambios |
| Inicio | Confirmación y vigencia |
| Live | Marcador, fase, último hecho y timeline |
| Descanso | Síntesis, eventos e invalidadores |
| Final | Resultado, hechos decisivos y aprendizaje |
| Aplazado/suspendido | Estado oficial y siguiente revisión |
| Stale | Última lectura congelada y limitación |
| Cobertura insuficiente | Hechos disponibles y ausencias explícitas |

## 12.7 Hogares canónicos

| Dato | Hogar |
|---|---|
| Identidad, hora, estado y marcador | Ancla del partido |
| Cambios desde la última visita | Resumen de cambio |
| Goles, tarjetas, sustituciones y fases | Timeline |
| Métricas por periodo | Estadísticas |
| Titulares, suplentes y cambios | Participantes |
| Árbitro, estadio y entrenadores | Contexto oficial |
| Forma, H2H, clasificación y lesiones | Contexto deportivo |
| Equipos, competición y jugadores | Relaciones de entidad |
| Razones, riesgos e invalidadores | SHARK |
| Mercado, selección, cuota y estado | Pick |
| Exposición y límites | Bankroll |
| Alertas y entrega | Continuidad Telegram |

## 12.8 Contrato de datos

Cada módulo debe recibir:

- fuente;
- timestamp;
- frescura;
- completitud;
- certification state;
- limitaciones;
- lifecycle;
- ID canónico.

No se permiten consultas independientes que redefinan el partido.

## 12.9 Contrato de membresía

### FREE

- identidad;
- estado;
- marcador;
- timeline básico;
- alineaciones confirmadas disponibles;
- estadísticas esenciales;
- frescura;
- entidades;
- seguimiento básico.

### PRO

- lectura SHARK;
- pick gobernado;
- razones;
- contraargumentos;
- riesgos;
- invalidadores;
- alertas ampliadas;
- contexto comparado.

### ELITE y ELITE+

- escenarios;
- análisis longitudinal;
- seguimiento avanzado;
- Bankroll voluntario;
- continuidad premium;
- aprendizaje ampliado.

La verdad deportiva es común.

## 12.10 Contrato SHARK

SHARK:

- responde a una pregunta;
- usa evidencia visible;
- separa interpretación;
- incluye contraargumento;
- declara riesgo;
- enumera invalidadores;
- puede recomendar esperar;
- puede permanecer en silencio.

## 12.11 Contrato Telegram

Telegram:

- requiere opt-in;
- identifica cambio;
- deduplica;
- respeta límites;
- usa hora Madrid;
- vuelve al contexto exacto;
- nunca rellena.

## 12.12 Contrato de rendimiento

- identidad y estado no dependen de módulos secundarios;
- ningún proveedor bloquea la primera lectura;
- profundidad puede diferirse;
- actualización no reinicia posición;
- imágenes usan fallback;
- timeline grande se agrupa o pagina;
- no se realizan escrituras DB por GET;
- no hay llamadas externas bloqueantes durante render.

## 12.13 Contrato responsive

Móvil y desktop comparten:

- misma verdad;
- misma fase;
- mismo timeline;
- mismos límites;
- mismas acciones permitidas.

Solo cambia la presentación y progresión.

## 12.14 Contrato de accesibilidad

- orden semántico estable;
- foco visible;
- teclado completo;
- cambios live anunciados con moderación;
- estados no dependientes del color;
- controles táctiles suficientes;
- movimiento reducible;
- tablas con lectura alternativa;
- texto y acciones sin recorte.

## 12.15 Contrato de retorno

Desde Calendario se conservan:

- fecha;
- carril;
- filtros;
- posición;
- partido de origen.

Desde entidades relacionadas se conserva:

- partido;
- fase;
- punto de lectura;
- cambios durante la ausencia.

---

# 13. Compatibilidad de calidad

## Browser QA

Debe cubrir:

- desktop;
- móvil;
- previa;
- live;
- descanso;
- final;
- stale;
- cobertura insuficiente;
- navegación;
- retorno;
- consola;
- overflow;
- foco;
- carga.

## Sentinel

Debe detectar:

- lifecycle incoherente;
- falso live;
- stale público;
- marcador no confirmado;
- evento duplicado;
- datos en hogar incorrecto;
- prioridad de fase incorrecta;
- SHARK invasivo;
- pick incompleto;
- verdad distinta por membresía;
- pérdida de contexto;
- regresión móvil.

## AutoPilot

Puede:

- crear incidencia;
- identificar contrato;
- reunir evidencia;
- proponer archivos y pruebas;
- requerir aprobación.

No puede modificar la arquitectura ni el código.

---

# 14. Validación contra las Biblias

## Product Bible

La decisión D:

- prioriza experiencia;
- usa una verdad;
- preserva contexto;
- reduce ruido;
- admite incertidumbre;
- mantiene FREE útil;
- respeta juego responsable;
- permite operación.

## Sports UX Bible

La decisión:

- confirma una historia única;
- conecta Calendario y entidades;
- integra cambio antes que repetición;
- mantiene Telegram como continuidad;
- mantiene SHARK como criterio.

## Match Center UX Bible

La decisión:

- utiliza las cinco alternativas evaluadas;
- respeta sus fortalezas y riesgos;
- convierte la comparación en un contrato;
- no introduce una sexta alternativa no estudiada.

---

# 15. Estado final

`MATCH_CENTER_ARCHITECTURE_APPROVED`

`PRIMARY_ARCHITECTURE = D_LIFECYCLE_STORY`

`CONTRACT = MATCH-CENTER-LIFECYCLE-STORY-V1`

`IMPLEMENTATION_READY`

`IMPLEMENTATION_EXECUTED = FALSE`

`PRODUCTION_MODIFIED = FALSE`

La arquitectura está decidida. La implementación solo podrá comenzar mediante incrementos pequeños, desplegables, verificables y reversibles.

