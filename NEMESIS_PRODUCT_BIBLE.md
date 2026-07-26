# NeMeSiS Product Bible

## 0. Control del documento

**Sprint estratégico:** `V942_NEMESIS_PRODUCT_BIBLE_FOUNDATION_FINAL`  
**Estado:** `PRODUCT_FOUNDATION_COMPLETE / IMPLEMENTATION_NOT_AUTHORIZED`  
**Naturaleza:** exclusivamente documental  
**Código autorizado:** no  
**Producción modificada:** no  
**Commit, push o deploy autorizados:** no  

V942 identifica la fundación documental del producto. No cambia el runtime, la base de datos ni la versión desplegada.

Esta Biblia es la referencia máxima para las decisiones de producto de NeMeSiS SHARK PRO. Toda propuesta futura debe poder responder:

1. qué problema real resuelve;
2. qué principio de esta Biblia cumple;
3. qué evidencia la justifica;
4. qué dato utiliza y con qué calidad;
5. qué experiencia mejora;
6. qué riesgo introduce;
7. cómo se valida;
8. cómo se opera y recupera;
9. por qué merece existir.

Si una propuesta no puede responder, no entra en el producto.

---

# 1. Resumen ejecutivo

## 1.1 Qué es NeMeSiS

NeMeSiS SHARK PRO es una plataforma deportiva de criterio, seguimiento y confianza.

No existe para mostrar la mayor cantidad posible de información. Existe para transformar información deportiva real en una experiencia comprensible:

```text
QUÉ OCURRE
→ QUÉ CAMBIÓ
→ QUÉ MERECE ATENCIÓN
→ QUÉ EVIDENCIA EXISTE
→ QUÉ RIESGO FALTA POR RESOLVER
→ QUÉ PUEDE HACER EL USUARIO AHORA
```

NeMeSiS une:

- deporte real;
- calidad y frescura del dato;
- navegación continua;
- criterio SHARK;
- picks gobernados;
- Telegram contextual;
- membresías con valor;
- operación verificable;
- aprendizaje basado en resultados;
- juego responsable.

## 1.2 La promesa

> NeMeSiS reduce el ruido deportivo para que cada usuario encuentre antes, entienda mejor y decida con más criterio, incluida la decisión de no actuar.

## 1.3 La diferencia

NeMeSiS no debe competir por acumulación de módulos. Debe competir por:

- claridad;
- continuidad;
- explicación;
- honestidad;
- capacidad de esperar;
- atención bien utilizada;
- operación profesional.

## 1.4 La unidad del producto

La unidad básica no es una pantalla. Es un recorrido completo:

```text
SITUAR
→ DESCUBRIR
→ ENTENDER
→ SEGUIR
→ DECIDIR O ESPERAR
→ RECORDAR
→ APRENDER
→ VOLVER CON CONTEXTO
```

---

# 2. Propósito

## 2.1 Por qué existe NeMeSiS

El deporte digital ofrece abundancia, pero no siempre comprensión. El usuario encuentra:

- listas extensas;
- estados sin contexto;
- datos de distinta calidad;
- alertas repetitivas;
- predicciones sin límites;
- cambios difíciles de seguir;
- recorridos fragmentados;
- presión comercial;
- ausencia de explicación cuando falta información.

NeMeSiS existe para convertir esa dispersión en una relación de confianza.

## 2.2 Qué problema resuelve

Resuelve cinco problemas fundamentales.

### Problema 1: encontrar

El usuario necesita localizar el partido, equipo, competición, jugador, pick o cambio relevante sin reconstruir el producto mediante scroll y memoria.

### Problema 2: comprender

El usuario necesita distinguir:

- hecho;
- contexto;
- cambio;
- interpretación;
- incertidumbre;
- acción.

### Problema 3: confiar

El usuario necesita saber:

- si el dato es real;
- cuándo se actualizó;
- si está completo;
- qué fuente o contrato lo sostiene;
- qué limitación existe;
- por qué un dato no aparece.

### Problema 4: continuar

El usuario necesita pasar de Calendario a partido, equipo, competición, jugador, SHARK o Telegram sin perder:

- entidad;
- fecha;
- fase;
- filtros;
- posición;
- propósito;
- contexto de retorno.

### Problema 5: decidir con responsabilidad

El usuario necesita criterio para:

- prestar atención;
- profundizar;
- seguir;
- esperar;
- ignorar;
- revisar una selección;
- no apostar.

## 2.3 Qué no pretende ser

NeMeSiS no pretende ser:

- un escaparate de funciones;
- una base de datos sin jerarquía;
- una máquina de predicciones;
- una promesa de ganancias;
- una casa de apuestas;
- un canal de spam;
- una fuente de urgencia artificial;
- un producto que oculta hechos básicos para forzar una compra;
- un sistema autónomo sin control humano;
- un panel técnico expuesto al cliente;
- una copia de otra aplicación;
- un producto que aparenta tiempo real cuando no lo tiene.

## 2.4 La frase que debe gobernar el producto

> NeMeSiS no vende apuestas. NeMeSiS vende criterio.

---

# 3. Autoridad y jerarquía de decisiones

## 3.1 Jerarquía documental

| Nivel | Documento o contrato | Responsabilidad |
|---|---|---|
| 1 | `NEMESIS_PRODUCT_BIBLE.md` | Propósito, principios y límites máximos del producto |
| 2 | `NEMESIS_SPORTS_UX_BIBLE.md` | Visión integrada de la experiencia deportiva |
| 3 | Biblias de experiencia, incluida `NEMESIS_MATCH_CENTER_UX_BIBLE.md` | Diseño funcional profundo de una experiencia concreta |
| 4 | Contratos de datos, lifecycle, privacidad, seguridad y membresía | Verdad operativa y reglas no negociables |
| 5 | Especificaciones técnicas | Traducción aprobada de una decisión a implementación |
| 6 | Backlogs, incidencias y sprints | Ejecución acotada y verificable |
| 7 | Código, templates y configuración | Implementación subordinada a todo lo anterior |

## 3.2 Restricciones superiores

La Biblia de Producto es la autoridad máxima de producto, pero nunca puede rebajar:

- legislación;
- privacidad;
- seguridad;
- consentimiento;
- derechos de datos y activos;
- protección de menores;
- juego responsable;
- integridad de pagos;
- protección de usuarios;
- conservación de datos reales.

## 3.3 Resolución de conflictos

Cuando dos objetivos compiten, el orden es:

1. seguridad, legalidad y protección de personas;
2. datos reales e integridad;
3. confianza y transparencia;
4. resolución de la tarea del usuario;
5. accesibilidad y calidad;
6. rendimiento y continuidad;
7. operación y recuperación;
8. valor comercial;
9. velocidad de entrega;
10. novedad.

Ningún objetivo comercial puede ganar a la verdad del dato.

---

# 4. Principios del producto

## 4.1 Simplicidad con profundidad

Simplicidad no significa ocultar lo importante. Significa:

- una pregunta por experiencia;
- una acción principal reconocible;
- información secundaria bajo una jerarquía clara;
- lenguaje comprensible;
- progresión natural;
- ausencia de duplicación.

Un producto simple permite profundizar sin hacer que todos carguen con toda la profundidad.

## 4.2 Rapidez real y percibida

La velocidad incluye:

- tiempo de respuesta;
- tiempo hasta comprender;
- tiempo hasta encontrar;
- estabilidad durante la carga;
- conservación de contexto;
- ausencia de esperas bloqueantes.

Una pantalla que carga rápido pero obliga a buscar durante un minuto no es rápida.

## 4.3 Confianza antes que persuasión

Toda decisión debe reforzar:

- origen;
- frescura;
- completitud;
- limitación;
- trazabilidad;
- coherencia entre módulos.

Cuando confianza y conversión entran en conflicto, gana la confianza.

## 4.4 Datos reales

NeMeSiS nunca presenta como real:

- un partido inventado;
- un marcador inferido;
- un minuto simulado;
- una cuota inexistente;
- un resultado no confirmado;
- una lesión deducida;
- una conversión no atribuible;
- un ingreso calculado sin fuente;
- un aprendizaje sin muestra.

## 4.5 Cero información inventada

La ausencia de información debe producir:

- estado seguro;
- explicación;
- limitación;
- siguiente revisión;
- acción permitida.

Nunca se rellena un hueco para que la interfaz parezca completa.

## 4.6 Transparencia útil

Transparencia no significa mostrar detalles técnicos al cliente. Significa explicar:

- qué sabemos;
- qué no sabemos;
- qué cambió;
- qué riesgo existe;
- qué se ha bloqueado;
- cuándo se revisó.

El diagnóstico técnico pertenece a admin. La explicación humana pertenece al cliente.

## 4.7 Calidad antes que cantidad

Más partidos, estadísticas, picks, mensajes o módulos no equivalen a más valor.

Antes de añadir algo, preguntar:

- ¿resuelve una tarea?
- ¿reduce esfuerzo?
- ¿aumenta comprensión?
- ¿evita abrir otra aplicación?
- ¿puede mantenerse con calidad?

## 4.8 Experiencia antes que funciones

Una función aislada no entra porque sea técnicamente posible. Debe formar parte de un recorrido:

- inicio;
- contexto;
- acción;
- resultado;
- retorno;
- recuperación.

## 4.9 Una verdad compartida

Todos los consumidores de una métrica o entidad deben usar el mismo contrato.

No se permiten:

- consultas paralelas con definiciones distintas;
- contadores locales presentados como globales;
- lifecycle incompatible;
- frescura diferente para el mismo dato;
- versiones distintas de una misma verdad según membresía.

## 4.10 Cambio antes que repetición

Al volver, NeMeSiS debe priorizar:

- qué cambió;
- qué sigue vigente;
- qué quedó stale;
- qué requiere atención.

No obliga al usuario a releer todo.

## 4.11 Contexto preservado

El producto debe conservar, cuando siga siendo válido:

- fecha;
- filtros;
- posición;
- entidad;
- fase;
- intención;
- punto de retorno.

## 4.12 Personalidad propia

NeMeSiS debe reconocerse por:

- criterio;
- serenidad;
- precisión;
- lenguaje claro;
- disciplina;
- capacidad de decir “no”;
- conexión natural entre deporte, SHARK y Telegram.

No por copiar una composición o acumular efectos visuales.

## 4.13 Móvil como producto principal

Móvil no es un escritorio comprimido. Debe:

- resolver la misma tarea;
- usar la misma verdad;
- preservar contexto;
- mantener acciones alcanzables;
- respetar safe area;
- evitar densidad y scroll innecesarios.

## 4.14 Accesibilidad desde el concepto

La accesibilidad no se añade al final. Toda experiencia debe considerar:

- orden de lectura;
- foco;
- teclado;
- contraste;
- estados no dependientes del color;
- lenguaje;
- tamaños táctiles;
- movimiento reducido;
- tecnologías de asistencia.

## 4.15 Operación como parte del producto

Una experiencia no está completa si la empresa no puede:

- saber si funciona;
- detectar una degradación;
- explicar un estado;
- identificar una dependencia;
- contener un fallo;
- recuperar;
- auditar;
- aprender.

## 4.16 Mejora basada en evidencia

NeMeSiS puede:

- observar;
- medir;
- detectar;
- recomendar;
- comparar;
- simular.

No puede declarar mejora sin:

- baseline;
- muestra;
- resultado;
- limitación;
- revisión.

---

# 5. Identidad

## 5.1 Cómo debe sentirse un usuario

El usuario debe sentir:

- **orientación:** sé dónde estoy;
- **control:** sé qué puedo hacer;
- **serenidad:** no me están empujando;
- **confianza:** entiendo la calidad del dato;
- **velocidad:** llego a lo importante;
- **criterio:** sé por qué algo merece atención;
- **continuidad:** puedo salir y volver;
- **respeto:** mi tiempo y mis límites importan.

## 5.2 Cómo debe sentirse un administrador

El administrador debe sentir:

- **visión:** entiendo qué está pasando;
- **prioridad:** sé qué necesita atención;
- **evidencia:** puedo investigar;
- **control:** una acción sensible no ocurre por accidente;
- **trazabilidad:** sé quién, cuándo y por qué;
- **recuperación:** existe siguiente paso y rollback;
- **responsabilidad:** no necesito adivinar el estado de la empresa.

## 5.3 Cómo debe sentirse la empresa

NeMeSiS debe operar como una organización:

- deliberada;
- auditable;
- honesta;
- preparada;
- aprendiente;
- responsable;
- comercialmente disciplinada.

## 5.4 Emociones que queremos transmitir

- claridad;
- confianza;
- calma;
- profesionalidad;
- precisión;
- pertenencia;
- curiosidad;
- dominio.

## 5.5 Emociones que evitamos

- ansiedad;
- urgencia artificial;
- confusión;
- sospecha;
- saturación;
- culpa;
- presión;
- miedo a perderse algo;
- falsa certeza.

---

# 6. Filosofía visual

La filosofía visual describe sensaciones y comportamiento, no colores.

## 6.1 Premium

Premium significa:

- cada elemento tiene una razón;
- la información está cuidada;
- el producto responde con estabilidad;
- el lenguaje es preciso;
- la ausencia está diseñada;
- los detalles no parecen accidentales.

Premium no significa más decoración.

## 6.2 Orden

El usuario debe percibir:

- principio;
- prioridad;
- relación;
- profundidad;
- cierre.

El orden reduce trabajo mental.

## 6.3 Claridad

Cada experiencia debe responder rápidamente:

- dónde estoy;
- qué ocurre;
- qué cambió;
- qué merece atención;
- qué puedo hacer.

## 6.4 Jerarquía

La jerarquía separa:

- hecho principal;
- contexto;
- criterio;
- acción;
- diagnóstico.

Todo no puede tener el mismo peso.

## 6.5 Velocidad

La interfaz debe sentirse inmediata porque:

- mantiene dimensiones estables;
- evita saltos;
- conserva posición;
- no bloquea todo por una dependencia;
- comunica actualización;
- reduce decisiones innecesarias.

## 6.6 Elegancia

Elegancia significa resolver complejidad sin exhibirla.

Se expresa mediante:

- proporción;
- consistencia;
- ritmo;
- lenguaje breve;
- transiciones justificadas;
- ausencia de ruido.

## 6.7 Densidad adecuada

La densidad depende de la tarea:

- descubrir requiere comparación;
- seguir requiere continuidad;
- decidir requiere evidencia;
- operar requiere prioridad;
- configurar requiere precisión.

No existe una única densidad correcta para todo el producto.

## 6.8 Movimiento con significado

Una animación solo existe si ayuda a:

- entender un cambio;
- mantener orientación;
- confirmar una acción;
- explicar una transición.

Nunca simula tiempo real, urgencia o éxito.

---

# 7. Filosofía de datos

## 7.1 La verdad del producto

El dato es parte de la experiencia y de la promesa comercial.

Todo dato visible debe tener:

- definición;
- origen;
- momento de captura;
- frescura;
- estado;
- limitación;
- consumidor autorizado.

## 7.2 Un único origen de verdad

Cuando sea posible:

- una métrica;
- una definición;
- un snapshot;
- un lifecycle;
- múltiples consumidores.

Si dos representaciones necesitan diferencias, estas deben ser de presentación, no de verdad.

## 7.3 Calidad frente a abundancia

NeMeSiS prioriza:

- dato útil;
- dato reciente;
- dato completo;
- dato comparable;
- dato explicable.

No premia:

- columnas vacías;
- ceros sustituyendo ausencia;
- cifras sin contexto;
- muestras irrelevantes;
- datos repetidos.

## 7.4 Incertidumbre visible

Estados mínimos de evidencia:

- confirmado;
- parcialmente confirmado;
- pendiente;
- stale;
- bloqueado por acceso;
- cobertura insuficiente;
- hipótesis;
- requiere revisión.

No todos los estados deben usar lenguaje técnico, pero su significado debe conservarse.

## 7.5 Calidad del dato no es probabilidad

El Índice de Confianza NeMeSiS mide calidad, completitud, frescura y verificabilidad.

No mide:

- probabilidad de ganar;
- certeza de un pick;
- garantía de resultado;
- confianza emocional.

## 7.6 Lifecycle coherente

Partido, live, pick, cuota y resultado deben avanzar mediante estados compatibles.

Nunca:

- un finalizado aparece como próximo;
- un stale aparece como live;
- un pick incompleto aparece público;
- una cuota expirada aparece activa;
- un resultado pendiente se usa como liquidado.

## 7.7 Corrección y memoria

Cuando una fuente corrige:

- se conserva trazabilidad;
- se actualizan consumidores;
- se revisan consecuencias;
- se explica el cambio cuando afecta al usuario;
- no se reescribe la historia silenciosamente.

## 7.8 Estados vacíos

Un estado vacío debe responder:

- qué falta;
- por qué;
- si es temporal;
- cuándo se revisó;
- qué puede hacer el usuario;
- qué sigue funcionando.

---

# 8. Filosofía SHARK

## 8.1 Qué representa

SHARK es el Director Deportivo de NeMeSiS.

Representa:

- criterio;
- síntesis;
- disciplina;
- contradicción útil;
- memoria;
- capacidad de esperar.

No representa omnisciencia.

## 8.2 Cuándo debe intervenir

SHARK interviene cuando:

- existe una pregunta concreta;
- la evidencia puede sostener una respuesta;
- cambió un dato relevante;
- hay un riesgo que explicar;
- existe un invalidado;
- comparar escenarios reduce esfuerzo;
- esperar es una recomendación útil.

## 8.3 Cuándo debe permanecer en silencio

SHARK permanece en silencio cuando:

- no existe evidencia suficiente;
- solo repetiría datos;
- la muestra no permite una lectura;
- la información está stale;
- su intervención añadiría presión;
- el usuario no ha solicitado profundidad;
- el partido no merece atención analítica.

El silencio puede comunicarse con una explicación breve.

## 8.4 Cómo aporta valor

Toda lectura SHARK debe separar:

1. evidencia;
2. interpretación;
3. contraargumento;
4. riesgo;
5. invalidadores;
6. limitaciones;
7. siguiente revisión.

## 8.5 Qué nunca debe hacer

- garantizar beneficios;
- inventar datos;
- ocultar incertidumbre;
- presentar correlación como causalidad;
- recomendar recuperar pérdidas;
- generar urgencia;
- cambiar stake automáticamente;
- modificar pesos sin aprobación y muestra;
- crear picks retrospectivos;
- usar lenguaje de autoridad para ocultar falta de evidencia.

## 8.6 SHARK distribuido

SHARK distribuido no significa SHARK en todas partes.

Significa que su criterio aparece:

- en el momento;
- con la profundidad;
- para la pregunta;
- en la entidad;
- con la evidencia adecuada.

---

# 9. Filosofía Telegram

## 9.1 Qué representa

Telegram es una extensión controlada de NeMeSiS.

No es:

- una cuota de mensajes;
- un canal de relleno;
- una repetición de la web;
- una herramienta de presión.

## 9.2 Qué hace un mensaje válido

Un mensaje válido tiene:

- motivo;
- contexto;
- entidad;
- momento;
- evidencia;
- audiencia;
- dedupe;
- límite;
- destino exacto;
- siguiente acción.

## 9.3 Respeto por la atención

Antes de enviar, preguntar:

- ¿ha cambiado algo?
- ¿es útil ahora?
- ¿el usuario lo pidió?
- ¿merece una interrupción?
- ¿ya se envió?
- ¿puede esperar?

## 9.4 Continuidad

Telegram debe:

- devolver al contexto exacto;
- conservar partido, estado o pick;
- hablar con la misma voz;
- respetar membresía;
- respetar horario Madrid;
- permitir control de frecuencia;
- permitir salir.

## 9.5 Qué nunca debe enviar

- contenido para rellenar;
- picks incompletos;
- cuotas inválidas;
- falsos live;
- datos stale presentados como actuales;
- mensajes duplicados;
- promesas;
- presión;
- contenido a un destino no autorizado.

---

# 10. Filosofía FREE, PRO y ELITE

## 10.1 Principio comercial

Las membresías venden más valor, no una verdad diferente.

Todos los niveles comparten:

- hechos reales;
- estados honestos;
- seguridad;
- privacidad;
- juego responsable;
- navegación funcional;
- datos básicos necesarios para comprender.

## 10.2 FREE

FREE debe hacer pensar:

> “Incluso gratis, NeMeSiS me ayuda”.

Debe aportar:

- orientación;
- descubrimiento;
- hechos deportivos básicos;
- estados y resultados reales;
- seguimiento esencial;
- transparencia;
- muestra honesta del valor premium.

No debe sentirse deliberadamente roto.

## 10.3 PRO

PRO debe hacer pensar:

> “Estoy entendiendo y tomando decisiones con más criterio”.

Puede aportar:

- análisis SHARK;
- picks completos y gobernados;
- razones;
- contraargumentos;
- riesgos;
- invalidadores;
- alertas contextuales;
- seguimiento;
- profundidad comparada.

## 10.4 ELITE

ELITE debe hacer pensar:

> “Tengo el nivel más profundo de análisis y continuidad disponible”.

Puede aportar, si existe evidencia:

- escenarios;
- seguimiento avanzado;
- memoria de decisiones;
- análisis longitudinal;
- contexto ampliado;
- continuidad premium con Telegram;
- Bankroll voluntario;
- servicio y soporte reforzados.

## 10.5 ELITE+

Si existe una variante ELITE+, debe ampliar servicio, continuidad o acompañamiento. Nunca crea:

- hechos exclusivos falsos;
- certeza adicional inventada;
- presión;
- promesas;
- privilegios inseguros.

## 10.6 Cómo demostrar valor antes de vender

- explicar qué resuelve;
- mostrar ejemplos reales autorizados;
- diferenciar profundidad;
- indicar límites;
- conservar utilidad FREE;
- permitir entender el beneficio antes del pago;
- usar resultados reales y metodología.

## 10.7 Qué nunca debe hacerse para convertir

- ocultar marcador o resultado básico;
- crear miedo a perderse algo;
- degradar intencionadamente FREE;
- usar SHARK como presión;
- esconder cancelación;
- inflar ROI;
- inventar testimonios;
- simular escasez;
- confundir plan con probabilidad de éxito;
- usar patrones oscuros.

---

# 11. Filosofía Admin

## 11.1 Qué es el admin

El admin es el centro operativo de la empresa.

En diez segundos debe responder:

- qué está pasando;
- qué está degradado;
- quién está afectado;
- qué riesgo existe;
- qué necesita atención;
- qué acción es segura;
- qué evidencia falta.

## 11.2 Contexto de toda acción

Antes de una acción, admin debe conocer:

- objetivo;
- alcance;
- efecto;
- reversibilidad;
- autorización;
- dependencia;
- riesgo;
- evidencia.

## 11.3 Investigación

Toda incidencia debe poder recorrer:

```text
SEÑAL
→ EVIDENCIA
→ CAUSA PROBABLE
→ IMPACTO
→ CONTENCIÓN
→ CORRECCIÓN
→ VALIDACIÓN
→ CIERRE
→ APRENDIZAJE
```

## 11.4 Acciones sensibles

Requieren aprobación humana:

- código;
- deploy;
- DB;
- usuarios;
- membresías;
- pagos;
- reembolsos;
- Telegram real;
- secretos;
- proveedores;
- borrado;
- restauración;
- cambio de modelo o pesos.

## 11.5 Lo que no pertenece al cliente

- stack traces;
- rutas internas;
- secretos;
- estados de workers;
- IDs operativos;
- errores de proveedor;
- detalles de DB;
- diagnósticos de Stripe;
- configuración de Telegram.

El cliente recibe explicación segura. El admin recibe diagnóstico.

---

# 12. Filosofía de calidad

## 12.1 Una función no termina cuando funciona

Termina cuando:

- resuelve el problema;
- respeta el contrato;
- funciona con datos reales y ausencia;
- funciona en desktop y móvil;
- es accesible;
- no rompe navegación;
- no expone información;
- tiene pruebas;
- puede operarse;
- puede recuperarse;
- tiene evidencia;
- está documentada.

## 12.2 Browser QA

Browser QA debe verificar:

- experiencia real;
- rutas;
- estado;
- scroll;
- overflow;
- foco;
- navegación;
- texto;
- botones;
- carga;
- consola;
- responsive;
- estados vacíos;
- datos seguros.

Capturar no equivale a revisar. Revisar implica comparar, clasificar y corregir.

No se declara pixel-perfect sin revisión humana.

## 12.3 Sentinel

Sentinel vigila contratos permanentes:

- datos;
- lifecycle;
- frescura;
- navegación;
- privacidad;
- seguridad;
- componentes;
- accesibilidad;
- operación;
- regresiones.

Sentinel debe detectar con evidencia, no producir ruido genérico.

## 12.4 AutoPilot

AutoPilot puede:

- clasificar;
- priorizar;
- crear incidencia;
- reunir evidencia;
- proponer;
- generar checklist;
- generar prompt.

No puede:

- cambiar código;
- modificar datos;
- publicar;
- desplegar;
- enviar;
- cobrar;
- borrar;
- aprobarse a sí mismo.

## 12.5 Documentación

La documentación debe explicar:

- propósito;
- contrato;
- decisión;
- limitaciones;
- operación;
- QA;
- rollback;
- estado real.

No debe servir para ocultar falta de evidencia.

## 12.6 Pruebas

La cobertura debe crecer con el riesgo:

- lógica: unitarias;
- contratos: regresión;
- rutas: smoke;
- templates: Jinja;
- navegación: enlaces;
- producto: Browser QA;
- datos: fixtures y contratos;
- operación: simulación segura;
- producción: evidencia real read-only.

## 12.7 Definición de evidencia

Separar siempre:

- confirmado;
- probado local;
- probado en producción;
- no certificado;
- hipótesis;
- bloqueado por acceso;
- requiere revisión.

## 12.8 Regla de cierre

Nunca cerrar una funcionalidad con:

- P0 abierto;
- P1 corregible abierto;
- ruta rota;
- dato falso;
- overflow;
- secreto;
- estado inseguro;
- operación no comprendida;
- rollback inexistente.

---

# 13. Filosofía de negocio

## 13.1 Cómo debe crecer

NeMeSiS crece mediante:

- confianza;
- utilidad recurrente;
- membresías;
- automatización controlada;
- inteligencia;
- retención ganada;
- reputación;
- soporte;
- disciplina de costes.

## 13.2 Confianza

La confianza es un activo comercial.

Se gana mediante:

- resultados reales;
- límites visibles;
- track record coherente;
- estados honestos;
- pagos claros;
- cancelación clara;
- soporte;
- estabilidad.

## 13.3 Recurrencia

El usuario vuelve porque:

- encuentra antes;
- sabe qué cambió;
- conserva contexto;
- recibe menos ruido;
- obtiene criterio;
- puede confiar.

No porque el producto fabrique ansiedad.

## 13.4 Membresías

La membresía debe:

- resolver una necesidad repetida;
- ahorrar esfuerzo;
- ampliar criterio;
- mejorar continuidad;
- ser comprensible;
- ser reversible.

## 13.5 Automatización

La automatización aumenta margen cuando:

- reduce trabajo repetitivo;
- respeta guardrails;
- registra decisiones;
- contiene fallos;
- evita duplicados;
- protege costes.

No aumenta margen si desplaza riesgo hacia el usuario.

## 13.6 Inteligencia

La inteligencia empresarial debe:

- detectar patrones;
- medir calidad;
- encontrar regresiones;
- priorizar;
- explicar limitaciones;
- ayudar a decidir.

No debe inventar métricas ni convertir correlación en causalidad.

## 13.7 Prácticas prohibidas

- promesas exageradas;
- ROI inventado;
- métricas vanity presentadas como negocio;
- testimonios falsos;
- precios opacos;
- cancelación difícil;
- presión mediante pérdidas;
- alertas compulsivas;
- contenido relleno;
- segmentación invasiva;
- datos falsos para vender.

## 13.8 Métricas empresariales

Solo se calculan con fuentes reales:

- usuarios activos;
- conversión;
- churn;
- MRR;
- ARPU;
- CAC;
- LTV;
- uso de SHARK;
- retorno desde Telegram;
- retención;
- soporte;
- disponibilidad;
- incidentes;
- coste de proveedor;
- coste por usuario.

Cuando faltan datos: `INSUFFICIENT_DATA`.

---

# 14. Juego responsable, privacidad y seguridad

## 14.1 Juego responsable

NeMeSiS debe:

- mostrar riesgo;
- evitar garantías;
- permitir pausa;
- tratar stake como orientativo;
- evitar recuperación de pérdidas;
- excluir menores;
- usar lenguaje sereno;
- limitar interrupciones;
- conservar control humano.

## 14.2 Privacidad

Recopilar únicamente lo necesario:

- propósito definido;
- consentimiento cuando aplica;
- retención controlada;
- identificadores internos;
- agregación;
- acceso mínimo;
- eliminación segura.

No fingerprinting invasivo.

## 14.3 Seguridad

Principios:

- mínimo privilegio;
- secretos fuera de código y logs;
- rutas admin protegidas;
- cron con header autorizado;
- firmas de webhooks;
- idempotencia;
- sesiones seguras;
- auditoría;
- rate limits;
- rollback;
- backup.

## 14.4 Pagos

Los pagos requieren:

- identidad de entorno;
- producto y precio correctos;
- webhook validado;
- idempotencia;
- membresía coherente;
- cancelación;
- retorno seguro;
- auditoría.

Nunca se prueba cobrando en producción sin autorización explícita.

---

# 15. Automatización y control humano

## 15.1 Automático seguro

Puede incluir:

- lectura;
- health checks;
- detección;
- clasificación;
- dedupe;
- informes;
- métricas;
- prompts;
- simulaciones no destructivas.

## 15.2 Automático con límites

Puede incluir:

- sincronización con usage guard;
- cache;
- backoff;
- grading con reglas certificadas;
- creación de candidatos;
- alertas internas;
- tareas operativas reversibles.

## 15.3 Automático con aprobación

Requiere persona:

- publicar picks;
- enviar Telegram sensible;
- cambiar pesos;
- modificar membresías;
- desplegar;
- restaurar;
- ejecutar migraciones;
- activar experimentos;
- cambiar precios.

## 15.4 Exclusivamente humano

- borrar usuarios;
- revelar o rotar secretos;
- cobrar o reembolsar fuera de flujo autorizado;
- decidir incidentes legales;
- aceptar riesgo de datos;
- aprobar cambios estratégicos;
- declarar producción certificada;
- decidir una alternativa de producto sin evidencia.

---

# 16. Arquitectura de experiencia

## 16.1 Principio

NeMeSiS es una experiencia continua de entidades conectadas:

```text
SPORTS HUB
→ CALENDARIO
→ MATCH CENTER
→ EQUIPO / COMPETICIÓN / JUGADOR
→ SHARK / PICK / TELEGRAM / BANKROLL
→ HISTÓRICO
→ APRENDIZAJE
```

El usuario puede entrar por cualquier punto y reconstruir contexto.

## 16.2 Responsabilidad de cada experiencia

| Experiencia | Responsabilidad |
|---|---|
| Calendario | Descubrir partidos sin perder contexto |
| Match Center | Seguir una historia única antes, durante y después |
| Sports Entity Model | Asegurar identidad y relaciones canónicas |
| Team Center | Entender el estado y trayectoria de un equipo |
| Competition Center | Entender qué está en juego y cómo evoluciona |
| Player Center | Entender disponibilidad, rol e impacto |
| Sports Hub | Preparar el día y la siguiente acción |
| SHARK distribuido | Aportar criterio donde resuelve una pregunta |
| Telegram Premium | Extender seguimiento y profundidad con respeto |
| Histórico | Convertir resultado en memoria y aprendizaje |
| Admin | Operar, investigar y recuperar |

## 16.3 No repetición

Cada dato tiene un hogar canónico.

Otros módulos:

- enlazan;
- resumen;
- contextualizan;
- explican.

No clonan.

---

# 17. Roadmap estratégico

No contiene fechas. Cada fase depende de los gates de la anterior.

## 17.1 Calendario

Objetivo:

- descubrir cualquier partido;
- mantener contexto;
- escalar de pocas a grandes colecciones;
- usar una verdad deportiva.

Estado documental:

- visión aprobada;
- primera implementación aceptada localmente;
- certificación de producción separada.

Gate:

- experiencia, datos, Browser QA, Sentinel y retorno validados.

## 17.2 Match Center

Objetivo:

- seguir el mismo partido antes, durante y después;
- responder qué cambió;
- conectar hechos, contexto, criterio y continuidad.

Estado:

- Biblia UX creada;
- alternativa final pendiente;
- implementación no autorizada.

Gate:

- prototipos comparables;
- pruebas con usuarios;
- cobertura real;
- decisión explícita.

## 17.3 Sports Entity Model

Objetivo:

- identidad canónica de partido, equipo, competición y jugador;
- relaciones consistentes;
- dedupe;
- lifecycle;
- navegación profunda.

Gate:

- contrato de entidades;
- migración segura;
- compatibilidad;
- privacidad;
- rollback.

## 17.4 Team Center

Objetivo:

- explicar qué le ocurre al equipo;
- conectar forma, calendario, clasificación, plantilla y seguimiento.

Gate:

- cobertura y derechos;
- modelo de equipo;
- experiencia aprobada.

## 17.5 Competition Center

Objetivo:

- explicar jornada, fase, clasificación y evolución.

Gate:

- reglas competitivas verificadas;
- temporadas y fases coherentes;
- cobertura suficiente.

## 17.6 Player Center

Objetivo:

- explicar disponibilidad, rol e impacto con métricas pertinentes.

Gate:

- identidad de jugador;
- cobertura por rol;
- lesiones con fuente;
- comparabilidad responsable.

## 17.7 Sports Hub

Objetivo:

- preparar el día;
- priorizar sin ocultar cobertura;
- proponer la siguiente acción correcta.

Gate:

- experiencias y entidades anteriores estables;
- personalización consentida;
- medición agregada.

## 17.8 SHARK distribuido

Objetivo:

- responder preguntas concretas dentro de cada experiencia;
- explicar cambios;
- declarar límites;
- recomendar esperar.

Gate:

- contratos;
- evidencia;
- muestras;
- gobierno;
- revisión humana.

## 17.9 Telegram Premium

Objetivo:

- llevar el momento correcto;
- aportar profundidad por membresía;
- devolver al contexto;
- respetar atención.

Gate:

- opt-in;
- dedupe;
- límites;
- atribución;
- QA de destino;
- formato y juego responsable.

## 17.10 Beta

Objetivo:

- validar utilidad, comprensión, confianza, estabilidad y operación con usuarios autorizados.

Gate:

- cero P0;
- cero P1 corregibles;
- soporte;
- observabilidad;
- backups;
- recuperación;
- privacidad;
- pagos controlados;
- datos reales.

## 17.11 Lanzamiento

Objetivo:

- abrir el producto con una promesa que la empresa puede cumplir y operar.

Gate:

- producción certificada;
- datos frescos;
- seguridad;
- pagos;
- Telegram;
- soporte;
- incident response;
- rollback;
- continuidad de negocio;
- métricas reales.

---

# 18. Test obligatorio para cualquier decisión futura

Toda propuesta debe presentar esta ficha.

## 18.1 Problema

- ¿Qué problema real existe?
- ¿Quién lo sufre?
- ¿Qué evidencia lo demuestra?

## 18.2 Resultado

- ¿Qué podrá hacer mejor el usuario?
- ¿Cómo sabremos que lo consiguió?

## 18.3 Encaje

- ¿Qué principio de esta Biblia cumple?
- ¿Qué documento de experiencia la autoriza?
- ¿Contradice una decisión anterior?

## 18.4 Datos

- ¿Qué datos necesita?
- ¿De dónde proceden?
- ¿Qué frescura?
- ¿Qué ocurre si faltan?

## 18.5 Experiencia

- ¿Reduce esfuerzo?
- ¿Mantiene contexto?
- ¿Funciona en móvil?
- ¿Es accesible?
- ¿Evita duplicación?

## 18.6 SHARK y Telegram

- ¿Deben intervenir?
- ¿Por qué?
- ¿Qué límite?
- ¿Qué ocurre si permanecen en silencio?

## 18.7 Membresía

- ¿Qué valor crea?
- ¿Qué nivel lo recibe?
- ¿FREE sigue siendo útil?
- ¿Existe presión comercial?

## 18.8 Riesgo

- seguridad;
- privacidad;
- datos;
- operación;
- reputación;
- legal;
- juego responsable;
- costes.

## 18.9 Calidad

- pruebas;
- Browser QA;
- Sentinel;
- AutoPilot;
- documentación;
- rendimiento;
- accesibilidad;
- rollback.

## 18.10 Decisión

Estados permitidos:

- `APPROVED_FOR_RESEARCH`;
- `APPROVED_FOR_SPECIFICATION`;
- `APPROVED_FOR_IMPLEMENTATION`;
- `APPROVED_FOR_BETA`;
- `REQUIRES_EVIDENCE`;
- `BLOCKED`;
- `REJECTED`.

Ningún estado se infiere.

---

# 19. Decisiones aceptables

Una decisión es aceptable cuando:

- resuelve un problema demostrado;
- usa datos reales;
- reduce esfuerzo;
- aumenta confianza;
- preserva contexto;
- tiene estado seguro;
- es accesible;
- puede operarse;
- puede recuperarse;
- tiene prueba;
- tiene propietario;
- tiene límite;
- tiene rollback;
- no degrada FREE artificialmente;
- no presiona al usuario.

---

# 20. Decisiones que nunca deberían tomarse

- inventar datos para completar una experiencia;
- presentar stale como actual;
- copiar una cifra de referencia como dato real;
- crear una función sin problema;
- duplicar una verdad;
- añadir SHARK como decoración;
- enviar Telegram por volumen;
- ocultar hechos básicos para vender;
- usar miedo o pérdidas para convertir;
- declarar aprendizaje sin muestra;
- desplegar sin rollback;
- modificar DB real sin protección;
- exponer secretos;
- mezclar cliente y admin;
- automatizar una acción irreversible;
- declarar producción validada sin evidencia;
- elegir una alternativa de diseño solo porque es más fácil;
- medir éxito únicamente por permanencia o clics;
- considerar terminada una función porque “se ve bien”.

---

# 21. Definición de producto terminado

Una experiencia está terminada cuando:

1. el problema está demostrado;
2. la solución está aprobada;
3. los datos tienen contrato;
4. el estado vacío es útil;
5. el lifecycle es correcto;
6. desktop y móvil son excelentes;
7. accesibilidad está validada;
8. rendimiento cumple la tarea;
9. Browser QA está revisado;
10. Sentinel protege el contrato;
11. AutoPilot puede detectar y proponer;
12. Company Intelligence puede medir sin invadir;
13. admin puede operar;
14. existe rollback;
15. producción está certificada por separado.

---

# 22. Guía para una persona que se incorpora

## Qué es NeMeSiS

Una plataforma deportiva de criterio que convierte datos reales en atención, comprensión y decisiones responsables.

## Cómo debe trabajar

```text
PROBLEMA
→ EVIDENCIA
→ CAUSA
→ CONTRATO
→ ESPECIFICACIÓN
→ APROBACIÓN
→ IMPLEMENTACIÓN
→ QA
→ OPERACIÓN
→ APRENDIZAJE
```

## Qué debe preguntar

- ¿Ayuda al usuario?
- ¿Es real?
- ¿Es comprensible?
- ¿Es necesario?
- ¿Es coherente?
- ¿Es seguro?
- ¿Es accesible?
- ¿Es operable?
- ¿Es responsable?
- ¿Puede demostrarse?

## Qué debe evitar

- añadir por añadir;
- asumir;
- ocultar;
- duplicar;
- presionar;
- automatizar sin límites;
- declarar sin evidencia.

---

# 23. Validación de coherencia

## Con Sports UX Bible

Esta Product Bible conserva:

- sistema de atención deportiva;
- contexto;
- una verdad;
- continuidad;
- SHARK como criterio;
- Telegram como extensión;
- FREE útil;
- juego responsable;
- operación separada del cliente.

No modifica `NEMESIS_SPORTS_UX_BIBLE.md`.

## Con Match Center UX Bible

Esta Product Bible conserva:

- una sola historia del partido;
- datos, interpretación y decisión separados;
- estados seguros;
- integración no invasiva de SHARK y Telegram;
- decisión entre alternativas pendiente.

No modifica `NEMESIS_MATCH_CENTER_UX_BIBLE.md` ni elige alternativa.

## Con el modelo de membresías

Conserva:

- FREE útil;
- PRO basado en criterio;
- ELITE basado en profundidad y continuidad;
- ELITE+ subordinado a los mismos límites;
- verdad deportiva común.

## Con datos reales

Mantiene:

- cero información inventada;
- incertidumbre explícita;
- fuente y frescura;
- contrato único;
- estados vacíos;
- no certificación cuando falta evidencia.

## Con juego responsable

Mantiene:

- ausencia de garantías;
- control del usuario;
- riesgo visible;
- stake orientativo;
- no recuperación de pérdidas;
- no urgencia artificial;
- no experimentos dañinos.

---

# 24. Estado final

`PRODUCT_FOUNDATION_COMPLETE`

`IMPLEMENTATION_NOT_AUTHORIZED`

`CODE_MODIFIED = FALSE`

`PRODUCTION_MODIFIED = FALSE`

`MATCH_CENTER_ALTERNATIVE_SELECTED = FALSE`

`SPORTS_UX_BIBLE_MODIFIED = FALSE`

`MATCH_CENTER_UX_BIBLE_MODIFIED = FALSE`

Esta Biblia define qué es NeMeSiS, cómo debe evolucionar, qué decisiones son aceptables y qué decisiones nunca deberían tomarse.

Su mandato final es sencillo:

> Construir menos, comprender más, demostrar todo y no sacrificar nunca la confianza.
