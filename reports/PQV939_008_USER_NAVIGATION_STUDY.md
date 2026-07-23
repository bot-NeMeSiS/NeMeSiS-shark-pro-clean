# PQV939-008 — Estudio de navegación y conservación de contexto

**Estado:** INVESTIGACIÓN COMPLETADA, SIN SOLUCIÓN ELEGIDA  
**Fecha:** 23 de julio de 2026, Madrid  
**Incidencia:** PQV939-008  
**Alcance:** Calendario / Partidos  
**Referencia principal:** vídeo oficial de NeMeSiS SHARK PRO, tramo 01:31-02:06  
**Producción modificada:** no  
**Código modificado:** no  
**Decisión de producto tomada:** no

## 1. Propósito

Este estudio investiga si el problema observado en PQV939-008 es la longitud de la lista o, con mayor precisión, la pérdida de contexto durante la exploración de una colección grande de partidos.

El documento no selecciona una solución. Su objetivo es separar:

- lo confirmado por el vídeo;
- lo confirmado por la estructura actual;
- lo que puede inferirse con cautela;
- lo que todavía requiere una prueba de usuarios.

La causa raíz conductual no se considerará cerrada hasta comparar varias alternativas con tareas equivalentes.

## 2. Fuentes y nivel de evidencia

| Fuente | Uso en este estudio | Estado |
|---|---|---|
| Vídeo oficial, 1360x720, duración aproximada 4:30 | Recorrido real visible por Partidos y comportamiento durante el scroll | CONFIRMADO |
| `PRODUCT_QUALITY_MASTER_REVIEW_V939.md` | Definición oficial, prioridad y timestamps de PQV939-008 | CONFIRMADO |
| Estructura actual de `calendar.html` | Orden de módulos, filtros y render de la colección | CONFIRMADO |
| Rutas y parámetros actuales de Calendario | Capacidades de consulta y consumidores | CONFIRMADO |
| Especificación canónica de `match_card` | Límites del componente que no deben reabrirse en esta incidencia | CONFIRMADO |
| Vídeo móvil | No existe evidencia móvil en la referencia examinada | NO MEDIDO |
| Prueba con un partido objetivo y usuarios representativos | No se realizó en el vídeo | NO MEDIDO |
| Uso real de búsqueda, filtros, favoritos o CTA | No se observa durante el tramo analizado | NO MEDIDO |

### Limitaciones

- El vídeo muestra un recorrido, no una prueba de usabilidad con una tarea definida.
- No se conoce qué partido intentaba encontrar la persona.
- No se abre ninguna ficha de partido durante el tramo analizado.
- No se puede atribuir intención a una pausa, desplazamiento o retroceso sin confirmación del usuario.
- La referencia permite estudiar la experiencia de escritorio, pero no certificar el coste en móvil.
- Los cambios visuales P1 ya resueltos, incluido el antiguo desequilibrio del rail, quedan fuera de este análisis.

## 3. Definición literal del problema

La incidencia oficial describe una lista de 108 partidos que exige un recorrido excesivo. En el vídeo, el usuario atraviesa la agenda durante aproximadamente 35 segundos y los controles globales de Calendario dejan de estar visibles.

El síntoma visible no es únicamente “hay mucho scroll”. El síntoma más relevante es:

> Durante la exploración profunda, el usuario conserva las tarjetas próximas a su posición, pero pierde la referencia global que explica dónde está, qué filtro está activo y cómo cambiar rápidamente de estrategia.

## 4. Análisis del vídeo

### 4.1 Secuencia observada

| Tramo aproximado | Contenido visible | Lectura |
|---|---|---|
| 00:24.8-00:31 | Entrada en Partidos, encabezado y controles | Se presenta el contexto general de la agenda |
| 00:31-01:31 | Primer bloque de calendario | El usuario comienza a recorrer fechas, competiciones y tarjetas |
| 01:31-01:49 | Descenso rápido por una colección extensa | La navegación se convierte principalmente en scroll vertical |
| 01:49-01:58 | Zona próxima al final y retroceso parcial | Se observa una necesidad de reorientación o revisión |
| 01:58-02:06 | Salida del recorrido de Partidos | No se abre un partido ni se completa una búsqueda visible |

Los timestamps son aproximados y se utilizan para describir la secuencia, no para atribuir una intención no observada.

### 4.2 Qué permanece visible

Durante la exploración profunda permanecen:

- la navegación global de la aplicación;
- las tarjetas situadas en el viewport;
- el encabezado local de liga o grupo cuando se alcanza;
- competición, equipos, hora, estado y nivel de confianza de cada tarjeta;
- la acción repetida `Ver partido`;
- el control de favorito cuando corresponde al estado autenticado.

### 4.3 Qué deja de estar visible

Al abandonar la cabecera de la colección dejan de estar disponibles de forma inmediata:

- la fecha o carril seleccionado;
- la consulta de búsqueda;
- los filtros de liga y país;
- el resumen de resultados y contadores;
- el estado general de sincronización y frescura;
- la relación entre la posición actual y el conjunto completo;
- un acceso directo visible para modificar los controles;
- el contexto general de “por qué aparecen estos partidos”.

El usuario conserva contexto local, pero pierde contexto global.

### 4.4 Comportamiento observado

La única acción repetida que el vídeo demuestra es el desplazamiento vertical.

El vídeo no demuestra:

- uso frecuente de búsqueda;
- uso frecuente de filtros;
- apertura de favoritos;
- apertura de una ficha;
- preferencia por liga, país o estado;
- abandono causado exclusivamente por la longitud.

La presencia repetida de botones no equivale a uso repetido. Por tanto, no se puede afirmar todavía qué control es el más valioso.

## 5. Estructura actual de la experiencia

Las rutas `/calendar`, `/calendario`, `/calendario-global`, `/partidos` y `/partidos/calendario` comparten la presentación principal de Calendario.

La página se organiza actualmente así:

1. Estado realtime y de sincronización.
2. Resumen del ciclo deportivo.
3. Panel de decisión.
4. Cuatro métricas de contexto.
5. Carriles de navegación.
6. Búsqueda y filtros visibles.
7. Grupos por día.
8. Grupos por liga dentro de cada día.
9. Tarjetas canónicas de partido.
10. Contexto de proveedor, cambio de fecha y siguiente acción al final de la colección.

### 5.1 Capacidades ya existentes

La lógica actual admite:

- carril;
- fecha;
- búsqueda textual;
- liga;
- equipo;
- país;
- estado;
- orden;
- presencia de pick;
- favoritos;
- resultados;
- directo;
- ventanas temporales.

La interfaz visible expone búsqueda, liga, país y carriles de intención. Algunas capacidades admitidas por la lógica no tienen un control directo equivalente en el bloque principal.

### 5.2 Mecanismo estructural confirmado

La colección se representa de forma lineal:

- todos los grupos seleccionados se recorren en secuencia;
- cada liga incorpora sus tarjetas;
- los controles preceden a la colección;
- parte del contexto operativo aparece después de la colección;
- no existe contexto local persistente de Calendario durante el tramo profundo observado.

Este mecanismo explica la pérdida de contexto. No demuestra todavía cuál de las alternativas posibles resolvería mejor la necesidad real.

## 6. Recorrido actual del usuario

### 6.1 Recorrido conceptual

1. Entra en Partidos.
2. Interpreta el estado del día.
3. Decide si explora, busca o filtra.
4. Comienza a recorrer días y ligas.
5. Compara tarjetas.
6. Se aleja de los controles iniciales.
7. Mantiene únicamente el contexto del grupo visible.
8. Si cambia de intención, debe recordar el estado anterior y recuperar los controles.
9. Puede abrir una ficha, retroceder, cambiar de ruta o abandonar la exploración.

### 6.2 Recorrido observado

1. Se muestra el contexto inicial.
2. El usuario recorre la lista.
3. Aumenta la velocidad de desplazamiento.
4. Llega cerca del final.
5. Retrocede parcialmente.
6. Sale de la pantalla sin abrir un partido visible.

No puede concluirse si encontró lo que buscaba.

## 7. Coste de navegación

### 7.1 Costes confirmados

| Coste | Evidencia |
|---|---|
| Desplazamiento prolongado | El tramo oficial dedica aproximadamente 35 segundos a recorrer la colección |
| Pérdida de controles | Búsqueda, filtros y carriles abandonan el viewport |
| Pérdida de resumen | Los contadores y el estado general dejan de estar visibles |
| Repetición visual | El usuario procesa muchas tarjetas con una estructura semejante |
| Reorientación | Se observa retroceso después de alcanzar una zona profunda |

### 7.2 Costes inferidos que requieren validación

| Coste posible | Estado |
|---|---|
| Recordar qué filtro estaba activo | INFERENCIA |
| Recordar qué ligas ya se revisaron | INFERENCIA |
| Volver al inicio para cambiar de estrategia | INFERENCIA |
| Abrir una tarjeta incorrecta por fatiga visual | NO MEDIDO |
| Abandonar antes de encontrar el partido | NO MEDIDO |
| Mayor coste en móvil por menor densidad vertical | HIPÓTESIS |

### 7.3 Tiempo para localizar un partido concreto

**No está certificado.**

El vídeo confirma la duración aproximada del recorrido general, pero no define:

- el partido objetivo;
- el punto de inicio de la búsqueda;
- el criterio conocido por el usuario;
- el momento exacto de éxito;
- si el usuario utilizó memoria previa.

No es válido convertir los 35 segundos del recorrido en “tiempo de localización”. Tampoco es válido asumir que una búsqueda lineal media consumiría la mitad sin una tarea controlada.

## 8. Respuestas a las seis preguntas de investigación

### 8.1 ¿Cuánto tarda un usuario en localizar un partido concreto?

No puede responderse con la evidencia actual. El vídeo demuestra un recorrido de aproximadamente 35 segundos por la agenda, no una localización completada.

Para medirlo se necesita definir un objetivo, por ejemplo:

- “Encuentra el partido del equipo X”;
- “Localiza un partido de la competición Y”;
- “Encuentra un partido en directo”;
- “Encuentra un partido con pick”.

### 8.2 ¿Qué información pierde mientras hace scroll?

Pierde acceso inmediato a:

- fecha o carril activo;
- consulta y filtros;
- número y composición de resultados;
- estado global de datos;
- posición dentro del conjunto;
- motivo por el que el partido forma parte de la vista.

No pierde la identidad del partido visible ni su contexto local inmediato.

### 8.3 ¿Qué elementos deberían permanecer visibles?

La evidencia permite definir necesidades de información, pero no todavía su representación:

- **Orientación temporal:** qué día o ventana se está explorando.
- **Orientación temática:** qué liga o agrupación está activa.
- **Estado de selección:** qué filtros modifican el conjunto.
- **Magnitud:** cuántos resultados forman parte de la vista.
- **Progreso:** en qué zona de la colección se encuentra el usuario.
- **Cambio de estrategia:** cómo volver a buscar o filtrar sin reconstruir el recorrido.
- **Frescura:** si la información visible sigue vigente.

Que una información deba estar disponible no significa necesariamente que deba ser sticky. Puede resolverse mediante persistencia, acceso rápido, agrupación u otra alternativa.

### 8.4 ¿Qué acciones realiza más veces?

**Confirmado:** scroll vertical.

**Disponibles repetidamente, pero no usadas en el vídeo:** abrir partido y marcar favorito.

**No observadas:** buscar, filtrar, cambiar carril o abrir detalle.

No existe evidencia suficiente para ordenar las acciones por frecuencia real de producto.

### 8.5 ¿Cuáles son los filtros más importantes?

La importancia debe relacionarse con la intención, no con una suposición de uso:

| Intención | Filtro o acceso relacionado | Disponibilidad actual |
|---|---|---|
| Encontrar un equipo o partido conocido | Búsqueda / equipo | Búsqueda visible; capacidad de equipo disponible en lógica |
| Explorar un día | Fecha / carril temporal | Visible |
| Explorar una competición | Liga | Visible |
| Ver lo que ocurre ahora | Directo / estado | Carril visible; estado admitido por lógica |
| Ver análisis disponibles | Con pick | Carril visible |
| Volver a intereses guardados | Favoritos | Carril disponible |
| Revisar partidos terminados | Resultados | Carril disponible |
| Acotar por ámbito | País | Visible |
| Priorizar el orden | Hora, liga, importancia o picks | Capacidad existente; no toda está expuesta directamente |

El orden de importancia entre estos filtros sigue siendo **NO MEDIDO**.

### 8.6 ¿Qué puede reducir el esfuerzo cognitivo?

Las oportunidades generales son:

- hacer visible el estado actual de la exploración;
- reducir la necesidad de recordar filtros;
- disminuir la exploración lineal cuando existe una intención concreta;
- facilitar el cambio de estrategia sin volver al inicio;
- diferenciar grupos sin alterar el contrato de la tarjeta;
- conservar el estado al entrar y volver de un partido;
- evitar que actualizaciones realtime reinicien la posición;
- mostrar solo contexto útil, sin crear una segunda navegación que compita con la principal.

Estas son condiciones de diseño, no una solución seleccionada.

## 9. Puntos donde el usuario puede perderse

| Punto | Qué ocurre | Estado de evidencia |
|---|---|---|
| Al abandonar la cabecera | Los controles dejan de estar visibles | CONFIRMADO |
| Entre ligas extensas | Solo queda el encabezado local del grupo visible | CONFIRMADO |
| Al cambiar de intención en profundidad | No hay acceso inmediato observado a los controles | CONFIRMADO EN ESTRUCTURA |
| Cerca del final | El contexto posterior llega después de toda la colección | CONFIRMADO EN ESTRUCTURA |
| Al retroceder | Debe reconstruir qué zonas ya recorrió | INFERENCIA |
| Tras abrir y volver de un partido | Puede perder posición o filtros | NO MEDIDO |
| En móvil | La menor densidad puede multiplicar el recorrido | HIPÓTESIS |
| Durante polling | Una actualización podría afectar posición o contexto | REQUIERE PRUEBA |

## 10. Alternativas a comparar

Ninguna alternativa queda recomendada o descartada en este estudio.

### A. Agrupación más fuerte

**Concepto:** reforzar la división por día, estado, liga u otra categoría verificable.

**Puede resolver:**

- dificultad para construir un mapa mental;
- repetición visual;
- necesidad de localizar una zona antes de una tarjeta.

**Riesgos:**

- ocultar partidos válidos si los grupos nacen cerrados;
- añadir pasos antes de ver el contenido;
- crear agrupaciones incompatibles con distintas intenciones;
- alterar el significado de contadores;
- hacer más compleja la navegación por teclado.

**Debe validarse:**

- tiempo para localizar liga y equipo;
- comprensión de los grupos;
- visibilidad de partidos no prioritarios;
- comportamiento en móvil.

### B. Navegación persistente

**Concepto:** mantener disponible una capa mínima de orientación o acceso a controles.

**Puede resolver:**

- pérdida de fecha, filtro o estrategia;
- coste de volver al inicio;
- falta de contexto global.

**Riesgos:**

- ocupar demasiado viewport;
- competir con topbar y bottom nav;
- producir una doble navegación;
- superponerse a tarjetas, modales o teclado móvil;
- mostrar un estado desactualizado tras polling.

**Debe validarse:**

- altura disponible;
- solapamientos;
- claridad entre navegación global y local;
- accesibilidad y foco.

### C. Filtros inteligentes

**Concepto:** dar acceso rápido a intenciones como Directo, Con pick, Favoritos o Resultados usando capacidades reales.

**Puede resolver:**

- exploración lineal cuando el objetivo es conocido;
- exceso de resultados irrelevantes para una intención concreta.

**Riesgos:**

- etiquetar como “inteligente” una regla estática;
- ocultar la lógica del filtro;
- crear combinaciones difíciles de comprender;
- personalizar sin señal suficiente;
- producir resultados vacíos que parezcan un fallo.

**Debe validarse:**

- comprensión del motivo de inclusión;
- facilidad para limpiar filtros;
- coherencia con Sports Data Contract;
- frecuencia real de cada intención.

### D. Búsqueda más accesible

**Concepto:** facilitar la localización por equipo, competición o texto sin cambiar la fuente de datos.

**Puede resolver:**

- búsqueda de un partido conocido;
- recorrido innecesario cuando existe un término concreto.

**Riesgos:**

- no ayudar al usuario que todavía no sabe qué busca;
- resultados incompletos por nombres alternativos;
- fricción con acentos o denominaciones de proveedor;
- duplicar campos de búsqueda;
- perder consulta al volver de detalle.

**Debe validarse:**

- tasa de éxito con nombres reales;
- tolerancia de coincidencia;
- persistencia de consulta;
- uso con teclado móvil.

### E. Sticky headers de día o liga

**Concepto:** conservar el encabezado contextual del grupo mientras se recorren sus tarjetas.

**Puede resolver:**

- pérdida de contexto local;
- duda sobre liga o fecha de la tarjeta visible.

**Riesgos:**

- resolver contexto local, pero no acceso a filtros;
- acumulación de capas sticky;
- cambios bruscos al pasar de grupo;
- problemas con lectores de pantalla o anclas;
- colisiones en viewport pequeño.

**Debe validarse:**

- transición entre grupos;
- altura de encabezado;
- compatibilidad con topbar;
- comportamiento con zoom.

### F. Favoritos como acceso rápido

**Concepto:** permitir que una colección personal reduzca el universo de exploración.

**Puede resolver:**

- visitas repetidas a equipos o partidos conocidos;
- coste recurrente de encontrar los mismos intereses.

**Riesgos:**

- no ayudar a usuarios nuevos;
- depender de sesión y estado persistente;
- confundir equipo favorito con partido favorito;
- introducir una colección vacía sin valor;
- asumir preferencias que no están medidas.

**Debe validarse:**

- comprensión del alcance;
- uso repetido;
- sincronización del estado;
- experiencia vacía.

### G. Índice o acceso rápido

**Concepto:** permitir saltar a un día, liga o sección sin recorrer todo lo anterior.

**Puede resolver:**

- distancia entre el inicio y una zona conocida;
- necesidad de retroceder;
- falta de un mapa de la colección.

**Riesgos:**

- añadir una segunda lista que también deba explorarse;
- desincronizar índice y contenido;
- demasiadas ligas para un control compacto;
- foco y scroll inesperados;
- complejidad cuando cambian filtros o polling.

**Debe validarse:**

- número máximo manejable de destinos;
- actualización del índice;
- navegación teclado;
- retorno a la posición anterior.

### H. Presentación progresiva

**Concepto:** mostrar la colección por etapas, páginas o grupos desplegables.

**Puede resolver:**

- longitud inicial;
- coste de render y percepción de densidad;
- sobrecarga visual.

**Riesgos:**

- ocultar partidos válidos;
- convertir la búsqueda global en parcial;
- perder el orden total;
- introducir más clics;
- romper enlaces, retorno y posición;
- distorsionar contadores o estados vacíos.

**Debe validarse:**

- descubrimiento de contenido oculto;
- continuidad al volver de detalle;
- semántica de filtros y métricas;
- accesibilidad sin JavaScript.

### I. Preservación de estado y posición

**Concepto:** conservar filtros, consulta y posición al entrar en un partido y volver.

**Puede resolver:**

- repetición del recorrido;
- pérdida de trabajo exploratorio;
- sensación de reinicio.

**Riesgos:**

- restaurar una posición inválida tras cambio de datos;
- mantener filtros que el usuario ya no recuerda;
- conflicto entre historial del navegador y estado interno;
- mayor complejidad de pruebas.

**Debe validarse:**

- navegación ida y vuelta;
- actualización realtime;
- enlaces compartidos;
- cierre y reapertura de sesión.

## 11. Comparación neutral

| Alternativa | Reduce recorrido lineal | Conserva contexto | Ayuda con objetivo conocido | Riesgo de ocultar contenido | Riesgo móvil |
|---|---|---|---|---|---|
| Agrupación | Potencialmente | Parcial | Parcial | Medio/alto | Medio |
| Navegación persistente | No necesariamente | Alto | Parcial | Bajo | Alto si ocupa demasiado |
| Filtros inteligentes | Alto para intenciones concretas | Medio | Alto | Medio | Medio |
| Búsqueda accesible | Alto | Bajo/medio | Alto | Bajo si busca todo el conjunto | Medio |
| Sticky headers | Bajo | Alto en contexto local | Bajo | Bajo | Medio/alto |
| Favoritos | Alto en visitas repetidas | Medio | Alto para intereses guardados | Bajo | Bajo/medio |
| Índice rápido | Alto | Alto | Alto por grupo | Bajo | Medio |
| Presentación progresiva | Alto visualmente | Medio | Parcial | Alto | Medio |
| Preservación de estado | Evita repetir recorrido | Alto | No reduce la primera búsqueda | Bajo | Bajo |

La tabla compara capacidades y riesgos conceptuales. No es una puntuación ni una recomendación.

## 12. Riesgos transversales

Cualquier solución futura debe evitar:

1. Ocultar partidos reales válidos.
2. Romper la definición canónica de métricas deportivas.
3. Permitir que cada módulo recalcule contadores.
4. Modificar el contrato de `match_card` sin una incidencia específica.
5. Crear navegación duplicada.
6. Apilar controles sticky sobre topbar o bottom nav.
7. Reiniciar el scroll por una actualización realtime.
8. Perder filtros al volver desde detalle.
9. Mostrar contexto stale después de polling.
10. Introducir personalización sin evidencia.
11. Hacer inaccesibles grupos, filtros o saltos mediante teclado.
12. Resolver el caso de 108 partidos deteriorando días con pocos eventos.
13. Confundir densidad visual con relevancia deportiva.
14. Mezclar esta incidencia con otros P2 o P3.

## 13. Protocolo de validación antes de decidir

### 13.1 Tareas comparables

Cada alternativa debería evaluarse con las mismas tareas:

1. Encontrar un partido por equipo.
2. Encontrar un partido de una liga indicada.
3. Encontrar un partido en directo.
4. Encontrar un partido con pick.
5. Cambiar de día después de recorrer una zona profunda.
6. Abrir un partido y volver al mismo punto.
7. Identificar qué filtros están activos sin volver al inicio.

### 13.2 Métricas

- éxito de la tarea;
- tiempo hasta el primer resultado correcto;
- distancia de scroll;
- número de retrocesos;
- aperturas incorrectas;
- cambios de filtro;
- tiempo para recuperar controles;
- capacidad de recordar fecha, liga y filtros;
- pérdida de posición al volver;
- errores de foco o navegación;
- altura útil ocupada en móvil.

### 13.3 Entornos

- escritorio 1366x768;
- móvil 390x844;
- colección grande comparable a la observada;
- colección pequeña;
- sin datos live;
- con datos live;
- con y sin resultados de búsqueda;
- sin llamadas externas y con snapshot controlado.

### 13.4 Evidencia mínima

Antes de elegir solución se necesita:

- baseline medido de la experiencia actual;
- al menos dos alternativas comparables;
- las mismas tareas y datos en cada alternativa;
- evidencia desktop y móvil;
- prueba de accesibilidad;
- confirmación de que no se ocultan partidos;
- confirmación de que filtros y contadores conservan su semántica;
- evaluación de retorno desde detalle.

## 14. Relación con Sports Experience

El estudio no contradice `PROJECT_NEMESIS_SPORTS_EXPERIENCE_MASTER_SPECIFICATION.md`.

La especificación ya exige:

- llegar al partido relevante con el mínimo esfuerzo;
- conservar fecha y filtros;
- agrupar con significado;
- explicar por qué aparece un partido;
- evitar que actualizaciones reinicien el recorrido.

PQV939-008 aporta la evidencia necesaria para decidir cómo cumplir esos principios en Calendario. La especificación permanece congelada y no se modifica en este Sprint.

## 15. Conclusión

### Confirmado

- La colección extensa exige un recorrido prolongado.
- Durante el recorrido se pierde el contexto global de Calendario.
- La navegación global permanece, pero la navegación contextual no.
- El usuario realiza scroll rápido y retrocede parcialmente.
- La estructura actual presenta controles antes de una colección lineal.
- Existen capacidades de filtrado que pueden reutilizarse sin crear motores.

### No certificado

- El tiempo real para encontrar un partido concreto.
- El filtro más importante para usuarios reales.
- Que el scroll sea por sí solo la causa principal.
- Que una solución sticky sea superior a búsqueda, agrupación o acceso rápido.
- El comportamiento móvil.
- El impacto en conversión, retención o satisfacción.

### Decisión

**No se elige ninguna solución.**

La causa estructural está identificada: el contexto y los controles quedan separados de una colección larga. La causa conductual definitiva permanece abierta: todavía debe determinarse si el mayor coste proviene de orientación, búsqueda, agrupación, persistencia o una combinación.

## 16. Siguiente puerta de decisión

La siguiente acción no es modificar `calendar.html`.

La siguiente acción es seleccionar, para una comparación controlada, al menos dos alternativas que ataquen mecanismos distintos, definir las tareas y medirlas frente al baseline. Solo después podrá fijarse la causa raíz definitiva y autorizar una corrección mínima para PQV939-008.

