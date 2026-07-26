# NeMeSiS Sports UX Bible

## Executive Summary

- **La mejor experiencia deportiva no es una colección de pantallas.** Es una historia continua que ayuda al usuario a descubrir qué importa, entender por qué, seguirlo en tiempo real, decidir con responsabilidad y recordar qué ocurrió.
- **NeMeSiS debe competir reduciendo ruido, no acumulando datos.** Su ventaja propia es unir deporte real, calidad del dato, SHARK, picks, Telegram y memoria del resultado sin confundir información, interpretación y recomendación.
- **La visión elegida es un sistema de atención deportiva.** Sports Hub prepara el día; Calendario organiza la exploración; Match Center conserva una única historia antes, durante y después; los centros de equipo, competición y jugador aportan contexto; Live comunica cambios, no animación vacía.
- **La preferencia del usuario todavía es una hipótesis.** Esta Biblia toma decisiones estratégicas, pero no afirma que un usuario vaya a abandonar otras aplicaciones hasta probar la experiencia en prototipos y beta privada.

## 1. Autoridad y estado

**Proyecto:** NeMeSiS Sports UX Lab  
**Estado:** `SPECIFICATION_ONLY`  
**Versión de producto de referencia:** V939  
**Código autorizado:** no  
**Implementación autorizada:** no  
**Producción modificada:** no  
**Datos reales modificados:** no  

Esta Biblia define la visión funcional futura de la experiencia deportiva. No autoriza:

- código;
- rutas;
- templates;
- CSS;
- nuevos motores;
- cambios de datos;
- llamadas a proveedores;
- envíos Telegram;
- cambios de membresía;
- experimentos con usuarios;
- push o deploy.

Los contratos activos de V939 sobre datos, privacidad, seguridad, SHARK, picks, Telegram, juego responsable y operación conservan prioridad normativa. La Biblia decide experiencia; no rebaja ningún guardrail.

## 2. La respuesta

### ¿Cómo debería ser la mejor experiencia deportiva del mundo?

Debería comportarse como un **director deportivo personal y verificable**:

1. Sitúa al usuario en menos de unos segundos.
2. Separa lo urgente de lo simplemente disponible.
3. Conserva el contexto al pasar de una entidad a otra.
4. Explica qué cambió y por qué importa.
5. Muestra fuente, frescura y limitaciones cuando afectan a la confianza.
6. Permite profundizar sin obligar a interpretar una base de datos.
7. Sigue el mismo partido antes, durante y después.
8. Recuerda intereses y decisiones con control del usuario.
9. Lleva la información adecuada a Telegram sin duplicar ruido.
10. Puede concluir honestamente: “Hoy no hay nada que merezca una decisión”.

La experiencia superior no intenta mantener al usuario dentro por fricción. Hace innecesario salir porque conserva continuidad, contexto y confianza.

## 3. Qué necesidad resuelve la categoría

No se realiza una comparación de funcionalidades ni se copian patrones de una aplicación concreta. Se abstraen los trabajos que cualquier producto deportivo serio debe resolver.

### 3.1 Trabajos fundamentales del usuario

| Trabajo | Pregunta real | Fallo que debe evitar NeMeSiS |
|---|---|---|
| Orientarse | ¿Qué está pasando ahora? | Mostrar una portada sin prioridad |
| Descubrir | ¿Qué merece mi atención? | Obligar a recorrer todo |
| Localizar | ¿Dónde está el partido, equipo o competición que busco? | Hacer depender la tarea de memoria y scroll |
| Comprender | ¿Por qué este dato importa? | Acumular estadísticas sin explicación |
| Seguir | ¿Qué cambió desde la última vez? | Repetir el estado completo sin destacar cambios |
| Confiar | ¿Es real, reciente y completo? | Disfrazar ausencia o stale como certeza |
| Decidir | ¿Debo actuar, esperar o ignorarlo? | Confundir recomendación con urgencia |
| Controlar | ¿Qué quiero seguir y por qué canal? | Alertas automáticas y ruido |
| Recordar | ¿Qué ocurrió y qué aprendimos? | Borrar el contexto al terminar |
| Regularse | ¿Qué exposición y riesgo estoy asumiendo? | Promover volumen o recuperación de pérdidas |

### 3.2 Necesidades emocionales

El usuario debe sentir:

- control sin esfuerzo;
- velocidad sin ansiedad;
- profundidad sin saturación;
- confianza sin falsa certeza;
- cercanía sin presión comercial;
- continuidad sin dependencia compulsiva;
- curiosidad sin perder orientación.

## 4. El Sports Experience Loop

La unidad básica de NeMeSiS no es la pantalla. Es este ciclo:

```text
SITUAR
→ DESCUBRIR
→ ENTENDER
→ SEGUIR
→ DECIDIR O ESPERAR
→ RECORDAR
→ APRENDER
→ PERSONALIZAR
→ VOLVER A SITUAR
```

### 4.1 Responsabilidad de cada experiencia

| Experiencia | Responsabilidad única |
|---|---|
| Sports Hub | Preparar el día y abrir la siguiente acción correcta |
| Calendario | Explorar toda la oferta sin perder contexto |
| Match Center | Mantener una sola historia del partido durante todo su ciclo |
| Team Center | Explicar el estado actual y la trayectoria de un equipo |
| Competition Center | Mostrar qué está en juego y cómo evoluciona la temporada |
| Player Center | Explicar disponibilidad, rol e impacto con contexto |
| Live Center | Comunicar cambios reales mientras ocurren |
| SHARK | Convertir evidencia en criterio y declarar límites |
| Telegram | Llevar el momento correcto al usuario y devolverlo al contexto |
| Admin | Explicar salud, cobertura, riesgo y siguiente acción operativa |

## 5. Principios no negociables

1. **Una verdad deportiva.** Todos los consumidores usan el Sports Data Contract oficial.
2. **Una historia por entidad.** La información no se duplica entre módulos sin una función distinta.
3. **Cambio antes que repetición.** Al regresar, el producto explica qué cambió.
4. **Contexto preservado.** Fecha, filtros, posición y entidad sobreviven al recorrido cuando siguen siendo válidos.
5. **Prioridad explicable.** Nada aparece “destacado” sin una razón visible y verificable.
6. **Cobertura honesta.** La falta de datos produce un estado útil, no contenido inventado.
7. **Tiempo real verificable.** Marcador, minuto, fase y eventos solo aparecen con evidencia fresca.
8. **SHARK sabe esperar.** No recomendar es una respuesta de alto valor.
9. **Telegram no rellena.** Cada mensaje tiene motivo, dedupe, límite y destino correcto.
10. **FREE comprende el deporte.** Los hechos básicos no se bloquean para fabricar conversión.
11. **PRO y ELITE profundizan.** Pagan por criterio, escenarios, seguimiento y continuidad, no por ocultar la realidad.
12. **Móvil es una experiencia primaria.** No es una versión comprimida de escritorio.
13. **Accesibilidad desde la decisión.** Foco, lectura, contraste, lenguaje y reducción de movimiento son parte del concepto.
14. **Privacidad proporcional.** Personalizar no autoriza fingerprinting ni recolección innecesaria.
15. **Juego responsable.** Ningún diseño optimiza presión, urgencia, pérdida o gasto compulsivo.
16. **Operación visible para la empresa, no para el cliente.** Diagnóstico técnico vive en admin.
17. **No hay autonomía peligrosa.** Datos, picks, mensajes y cambios sensibles conservan aprobación y auditoría.

## 6. Criterio de preferencia

Una alternativa solo puede considerarse superior si:

- resuelve una tarea completa mejor que una lista genérica;
- reduce cambios de aplicación;
- mantiene confianza y contexto;
- funciona con datos incompletos;
- conserva utilidad en móvil;
- escala a más competiciones sin generar más ruido;
- permite a SHARK explicar, no decorar;
- permite a Telegram extender, no duplicar;
- puede operarse y auditarse;
- evita presión irresponsable.

No basta con parecer innovadora.

## 7. Método del Product Board

### 7.1 Escala

Las puntuaciones son **juicio estratégico del Sports UX Lab**, no métricas de usuarios ni resultados comerciales.

| Puntuación | Significado |
|---:|---|
| 5 | Encaje excepcional con el mandato del rol |
| 4 | Encaje fuerte con riesgos controlables |
| 3 | Viable, pero con compromisos materiales |
| 2 | Débil o dependiente de mitigaciones importantes |
| 1 | Contradice una necesidad o guardrail relevante |

### 7.2 Panel

| Código | Perspectiva |
|---|---|
| CEO | Dirección general |
| COO | Operación de empresa |
| CTO | Tecnología |
| CPO | Producto |
| CDO | Diseño |
| COpO | Operaciones de producto |
| CRO | Ingresos |
| CCO | Cliente |
| UX | Investigación y experiencia |
| PROD | Gestión de producto |
| FE | Frontend |
| BE | Backend |
| SHARK | Inteligencia deportiva |
| TG | Telegram |
| DATA | Datos deportivos |
| QA | Calidad |
| SENT | Sentinel |
| AP | AutoPilot |
| CI | Company Intelligence |
| OPS | Operations Center |
| REC | Recovery |
| GROWTH | Crecimiento |
| CS | Customer Success |

### 7.3 Vetos

Una alternativa queda descartada aunque puntúe bien si:

- exige datos que no pueden certificarse;
- presenta confianza como probabilidad;
- oculta partidos válidos;
- degrada accesibilidad;
- fomenta conducta dañina;
- no puede operar en modo seguro;
- depende de personalización opaca;
- impide auditoría o recuperación.

# 8. Experiencia de descubrir partidos: Calendario

## 8.1 Resultado que debe producir

El usuario debe poder responder sin perderse:

- qué ocurre hoy;
- qué ocurre ahora;
- qué merece atención;
- dónde está un partido concreto;
- por qué aparece;
- cómo volver al mismo contexto.

## 8.2 Alternativa A: Agenda cronológica continua

**Concepto:** una única secuencia por hora, con agrupación temporal estable.

- **Ventajas:** predecible, fácil de aprender, completa y compatible con baja personalización.
- **Desventajas:** escala mal en jornadas grandes y obliga a escanear mucho.
- **Complejidad:** baja.
- **Escalabilidad:** técnica alta; cognitiva baja cuando crece la cobertura.
- **Valor usuario:** seguridad de que todo está presente.
- **Valor empresa:** coste operativo bajo y comportamiento fácil de medir.
- **Valor SHARK:** puede añadir contexto, pero corre el riesgo de repetir señales en muchas filas.
- **Valor Telegram:** enlaza fácilmente a una posición temporal.
- **Valor móvil:** débil en colecciones extensas.
- **Valor desktop:** bueno con densidad controlada.
- **Riesgo principal:** convertir cobertura en fatiga.

## 8.3 Alternativa B: Carriles por intención

**Concepto:** el usuario entra por “Ahora”, “Con pick”, “Favoritos”, “Próximos” o “Resultados”.

- **Ventajas:** reduce el universo según la tarea y comunica propósito.
- **Desventajas:** un partido puede pertenecer a varios carriles y la cobertura completa queda menos evidente.
- **Complejidad:** media.
- **Escalabilidad:** alta si las definiciones permanecen canónicas.
- **Valor usuario:** acceso rápido a una intención concreta.
- **Valor empresa:** mejora medición de tareas y conversión contextual.
- **Valor SHARK:** permite mostrar atención solo donde aporta.
- **Valor Telegram:** encaja con alertas y picks por intención.
- **Valor móvil:** alto por la reducción inicial de resultados.
- **Valor desktop:** alto, aunque puede infrautilizar el espacio.
- **Riesgo principal:** redefinir métricas globales desde filtros locales.

## 8.4 Alternativa C: Atlas de competiciones

**Concepto:** explorar primero país y competición; después jornada y partido.

- **Ventajas:** mapa mental fuerte para usuarios centrados en ligas.
- **Desventajas:** añade profundidad para quien solo busca “qué pasa ahora”.
- **Complejidad:** media.
- **Escalabilidad:** alta con una taxonomía de competiciones gobernada.
- **Valor usuario:** comprensión clara de cobertura y pertenencia.
- **Valor empresa:** facilita expansión y merchandising por competición.
- **Valor SHARK:** permite contexto agregado y comparabilidad.
- **Valor Telegram:** configura alertas por competición con precisión.
- **Valor móvil:** medio; demasiadas capas pueden ralentizar.
- **Valor desktop:** alto para exploración amplia.
- **Riesgo principal:** organizar según el proveedor y no según la intención humana.

## 8.5 Alternativa D: Radar personal

**Concepto:** favoritos, hábitos consentidos y alertas configuran una agenda personal.

- **Ventajas:** muy relevante, rápida en visitas recurrentes y fuerte para retención.
- **Desventajas:** valor inicial bajo y riesgo de burbuja o personalización opaca.
- **Complejidad:** alta.
- **Escalabilidad:** alta si la identidad y preferencias son consistentes.
- **Valor usuario:** menos ruido en el uso diario.
- **Valor empresa:** retención, alertas y membresía.
- **Valor SHARK:** prioriza explicaciones sobre intereses reales.
- **Valor Telegram:** excelente continuidad entre seguimiento y mensaje.
- **Valor móvil:** muy alto.
- **Valor desktop:** alto.
- **Riesgo principal:** confundir preferencia con importancia deportiva.

## 8.6 Alternativa E: Historia del día por capas

**Concepto:** una columna temporal completa actúa como columna vertebral; sobre ella, el usuario activa capas explicables de intención, competición, favoritos y atención SHARK, conservando siempre fecha, filtros y posición.

- **Ventajas:** combina cobertura, orientación, intención y personalización controlada.
- **Desventajas:** exige una jerarquía rigurosa para no convertirse en un híbrido sobrecargado.
- **Complejidad:** alta.
- **Escalabilidad:** alta si cada capa reutiliza el mismo contrato y no duplica colecciones.
- **Valor usuario:** descubre, localiza y vuelve sin reconstruir el recorrido.
- **Valor empresa:** crea un modelo común para adquisición, retención y medición.
- **Valor SHARK:** aporta una capa de atención, no una predicción repetida.
- **Valor Telegram:** conecta alertas con la misma entidad, capa y estado.
- **Valor móvil:** alto si la navegación contextual ocupa poco y los filtros son temporales.
- **Valor desktop:** muy alto por permitir visión y profundidad simultáneas.
- **Riesgo principal:** añadir demasiadas capas o hacer que una capa oculte cobertura válida.

## 8.7 Matriz de decisión: Calendario

### Dirección, cliente y crecimiento

| Alt. | CEO | COO | CPO | CDO | CRO | CCO | GROWTH | CS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 4 | 4 | 3 | 3 | 3 | 4 | 3 | 4 |
| B | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| C | 3 | 4 | 3 | 4 | 3 | 3 | 3 | 3 |
| D | 4 | 3 | 5 | 4 | 5 | 5 | 5 | 5 |
| E | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |

### Producto, tecnología y datos

| Alt. | CTO | UX | PROD | FE | BE | DATA | QA |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 5 | 3 | 3 | 5 | 5 | 5 | 5 |
| B | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| C | 4 | 3 | 3 | 4 | 4 | 5 | 4 |
| D | 3 | 5 | 5 | 3 | 3 | 3 | 3 |
| E | 4 | 5 | 5 | 4 | 4 | 5 | 5 |

### Inteligencia, operación y recuperación

| Alt. | COpO | SHARK | TG | SENT | AP | CI | OPS | REC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 5 | 3 | 4 | 5 | 4 | 4 | 5 | 5 |
| B | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| C | 4 | 3 | 3 | 4 | 4 | 4 | 4 | 4 |
| D | 3 | 4 | 5 | 3 | 4 | 5 | 3 | 3 |
| E | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 4 |

## 8.8 Decisión de Calendario

**Elegida: Alternativa E, Historia del día por capas.**

No gana por reunir todas las ideas. Gana porque conserva una columna vertebral completa y permite reducir esfuerzo sin esconder cobertura. Sus capas deben ser pocas, reversibles, acumulables y explicables.

Se descarta:

- A como visión final, porque no resuelve la escala cognitiva;
- B como sistema único, porque separa demasiado la agenda;
- C como entrada principal, porque antepone taxonomía a intención;
- D como base, porque depende de aprendizaje y uso previo.

La implementación futura solo podrá avanzar después de medir PQV939-008 con baseline y prototipos.

# 9. Experiencia de seguir un partido: Match Center

## 9.1 Resultado que debe producir

El usuario debe sentir que sigue **el mismo partido** antes, durante y después. No debe reaprender una pantalla distinta en cada estado.

## 9.2 Alternativa A: Dossier deportivo

**Concepto:** información organizada por áreas estables: previa, alineaciones, forma, estadísticas, picks e histórico.

- **Ventajas:** exhaustivo, auditable y familiar para análisis profundo.
- **Desventajas:** obliga al usuario a construir la historia por su cuenta.
- **Complejidad:** media.
- **Escalabilidad:** alta si los módulos degradan con cobertura limitada.
- **Valor usuario:** consulta completa.
- **Valor empresa:** fácil segmentación premium.
- **Valor SHARK:** muchas fuentes disponibles, pero explicación fragmentada.
- **Valor Telegram:** enlaces precisos a módulos.
- **Valor móvil:** medio por longitud y navegación entre secciones.
- **Valor desktop:** alto.
- **Riesgo principal:** convertirse en un archivo de datos.

## 9.3 Alternativa B: Línea temporal total

**Concepto:** todo se organiza cronológicamente desde la primera previa hasta el resultado final.

- **Ventajas:** continuidad natural y excelente memoria de cambios.
- **Desventajas:** los datos estructurales importantes pueden quedar dispersos.
- **Complejidad:** alta.
- **Escalabilidad:** media; muchos eventos producen ruido.
- **Valor usuario:** comprensión de “qué pasó después”.
- **Valor empresa:** retorno frecuente y alertas contextuales.
- **Valor SHARK:** explica cambios contra hipótesis anteriores.
- **Valor Telegram:** cada mensaje entra como un hito verificable.
- **Valor móvil:** alto.
- **Valor desktop:** medio/alto.
- **Riesgo principal:** confundir actividad con relevancia.

## 9.4 Alternativa C: Sala de decisión

**Concepto:** el partido se organiza alrededor de evidencia, razones, riesgos, invalidadores, pick y exposición.

- **Ventajas:** diferencia fuerte de NeMeSiS y máxima claridad para decidir.
- **Desventajas:** puede reducir el partido a una oportunidad de apuesta.
- **Complejidad:** alta.
- **Escalabilidad:** media por dependencia de datos y análisis.
- **Valor usuario:** criterio concentrado.
- **Valor empresa:** valor premium claro.
- **Valor SHARK:** central.
- **Valor Telegram:** conexión directa con picks y alertas.
- **Valor móvil:** alto si la decisión es breve.
- **Valor desktop:** alto para escenarios.
- **Riesgo principal:** contradecir la filosofía de que NeMeSiS vende criterio, no apuestas.

## 9.5 Alternativa D: Historia viva por ciclo

**Concepto:** una identidad y cabecera constantes; el cuerpo cambia de prioridad según previo, live, final o dato insuficiente. Cada fase explica estado, cambios y siguiente momento relevante.

- **Ventajas:** continuidad, contexto y foco sin duplicar pantallas.
- **Desventajas:** requiere reglas editoriales rigurosas para decidir qué sube o baja.
- **Complejidad:** alta.
- **Escalabilidad:** alta con módulos gobernados por disponibilidad real.
- **Valor usuario:** un único lugar para todo el ciclo.
- **Valor empresa:** retorno, confianza y profundidad premium sin romper hechos básicos.
- **Valor SHARK:** interpreta solo la fase y evidencia actuales.
- **Valor Telegram:** cada alerta devuelve al punto exacto de la historia.
- **Valor móvil:** muy alto por priorización secuencial.
- **Valor desktop:** muy alto con resumen y profundidad coordinados.
- **Riesgo principal:** transiciones incorrectas si el lifecycle o la frescura fallan.

## 9.6 Alternativa E: Dos modos, rápido y experto

**Concepto:** el usuario alterna entre una lectura esencial y otra completa.

- **Ventajas:** sirve a perfiles distintos y reduce densidad inicial.
- **Desventajas:** duplica decisiones editoriales y puede ocultar información sin que el usuario lo sepa.
- **Complejidad:** alta.
- **Escalabilidad:** media.
- **Valor usuario:** control explícito de profundidad.
- **Valor empresa:** segmentación y educación progresiva.
- **Valor SHARK:** resumen en modo rápido y evidencia en experto.
- **Valor Telegram:** puede enlazar al modo adecuado.
- **Valor móvil:** alto.
- **Valor desktop:** alto.
- **Riesgo principal:** mantener dos productos incoherentes.

## 9.7 Matriz de decisión: Match Center

### Dirección, cliente y crecimiento

| Alt. | CEO | COO | CPO | CDO | CRO | CCO | GROWTH | CS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 4 | 4 | 3 | 3 | 4 | 4 | 3 | 4 |
| B | 4 | 3 | 4 | 5 | 4 | 4 | 4 | 4 |
| C | 4 | 3 | 4 | 4 | 5 | 3 | 5 | 3 |
| D | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| E | 4 | 3 | 4 | 4 | 4 | 4 | 4 | 4 |

### Producto, tecnología y datos

| Alt. | CTO | UX | PROD | FE | BE | DATA | QA |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 4 | 3 | 4 | 4 | 4 | 5 | 5 |
| B | 3 | 5 | 4 | 3 | 3 | 4 | 3 |
| C | 3 | 4 | 4 | 3 | 3 | 4 | 3 |
| D | 4 | 5 | 5 | 4 | 4 | 5 | 5 |
| E | 3 | 4 | 3 | 3 | 3 | 4 | 3 |

### Inteligencia, operación y recuperación

| Alt. | COpO | SHARK | TG | SENT | AP | CI | OPS | REC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 4 | 4 | 4 | 5 | 4 | 4 | 5 | 5 |
| B | 3 | 5 | 5 | 3 | 4 | 4 | 3 | 3 |
| C | 3 | 5 | 5 | 4 | 4 | 4 | 3 | 3 |
| D | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| E | 3 | 4 | 4 | 3 | 3 | 4 | 3 | 3 |

## 9.8 Decisión de Match Center

**Elegida: Alternativa D, Historia viva por ciclo.**

La experiencia conserva una identidad estable y cambia prioridades, no estructura mental. El partido nunca se reduce a un pick: el análisis aparece dentro de su historia y puede concluir que no existe decisión responsable.

La línea temporal de B se conserva como módulo de hechos; el rigor del dossier A alimenta la evidencia; la sala C queda subordinada al contexto. No se mantienen dos productos separados como propone E.


# 10. Experiencia de seguir un equipo: Team Center

## 10.1 Resultado que debe producir

El usuario debe entender en una visita:

- cómo llega el equipo;
- qué cambió;
- qué partido viene;
- qué condiciona su estado;
- qué merece seguimiento.

## 10.2 Alternativa A: Perfil de club

**Concepto:** identidad, plantilla, calendario, clasificación y estadísticas en secciones estables.

- **Ventajas:** completo, predecible y fácil de indexar.
- **Desventajas:** responde “qué contiene” mejor que “qué le ocurre ahora”.
- **Complejidad:** baja/media.
- **Escalabilidad:** alta.
- **Valor usuario:** referencia fiable.
- **Valor empresa:** amplia cobertura con coste controlado.
- **Valor SHARK:** base de datos clara, pero contexto fragmentado.
- **Valor Telegram:** alertas simples por equipo.
- **Valor móvil:** medio por profundidad de secciones.
- **Valor desktop:** alto.
- **Riesgo principal:** ser un directorio sin narrativa.

## 10.3 Alternativa B: Pulso de equipo

**Concepto:** una lectura actual que combina próximo reto, cambio desde el último partido, forma contextual, disponibilidad, posición competitiva y seguimiento elegido.

- **Ventajas:** responde rápido qué vive el equipo y por qué.
- **Desventajas:** necesita priorización editorial consistente y estados honestos cuando faltan fuentes.
- **Complejidad:** alta.
- **Escalabilidad:** alta si se basa en módulos independientes y cobertura declarada.
- **Valor usuario:** seguimiento continuo sin reconstruir el contexto.
- **Valor empresa:** recurrencia, favoritos y alertas con significado.
- **Valor SHARK:** explica tendencias e invalidadores alrededor de una pregunta concreta.
- **Valor Telegram:** comunica cambios del pulso, no resúmenes repetidos.
- **Valor móvil:** muy alto por su jerarquía de “ahora, después, profundidad”.
- **Valor desktop:** muy alto.
- **Riesgo principal:** fabricar un “pulso” cuando la muestra o cobertura no existe.

## 10.4 Alternativa C: Laboratorio táctico

**Concepto:** identidad de juego, estructuras, zonas, comparaciones y rendimiento por fase.

- **Ventajas:** profundidad diferencial para usuarios expertos.
- **Desventajas:** cobertura costosa, interpretación compleja y alto riesgo de falsa precisión.
- **Complejidad:** muy alta.
- **Escalabilidad:** baja/media según proveedor.
- **Valor usuario:** alto para un segmento especializado.
- **Valor empresa:** propuesta ELITE potente si puede certificarse.
- **Valor SHARK:** alto cuando la metodología y muestra son sólidas.
- **Valor Telegram:** bajo; el contexto pierde valor al comprimirse.
- **Valor móvil:** bajo/medio.
- **Valor desktop:** alto.
- **Riesgo principal:** presentar inferencia táctica como dato confirmado.

## 10.5 Alternativa D: Sala de seguimiento personal

**Concepto:** el equipo se organiza alrededor de favoritos, alertas, jugadores seguidos, próximos partidos y recuerdos del usuario.

- **Ventajas:** relación personal fuerte y elevada utilidad recurrente.
- **Desventajas:** débil para primera visita y dependiente de preferencias.
- **Complejidad:** alta.
- **Escalabilidad:** alta con identidad de entidades estable.
- **Valor usuario:** control de lo que desea seguir.
- **Valor empresa:** retención y valor de cuenta.
- **Valor SHARK:** concentra análisis en intereses consentidos.
- **Valor Telegram:** excelente.
- **Valor móvil:** muy alto.
- **Valor desktop:** alto.
- **Riesgo principal:** priorizar afecto sobre relevancia verificable.

## 10.6 Alternativa E: Archivo de temporada

**Concepto:** recorrido histórico por jornadas, cambios de plantilla, resultados, rachas y momentos.

- **Ventajas:** memoria y aprendizaje excepcionales.
- **Desventajas:** no prioriza lo que debe hacerse ahora.
- **Complejidad:** media/alta.
- **Escalabilidad:** alta si el histórico es completo.
- **Valor usuario:** comprensión de trayectoria.
- **Valor empresa:** retención por archivo y contenido durable.
- **Valor SHARK:** permite comparar hipótesis con resultados.
- **Valor Telegram:** sirve como referencia posterior, no como motor de alertas.
- **Valor móvil:** medio.
- **Valor desktop:** alto.
- **Riesgo principal:** histórico parcial presentado como narrativa completa.

## 10.7 Matriz de decisión: Team Center

### Dirección, cliente y crecimiento

| Alt. | CEO | COO | CPO | CDO | CRO | CCO | GROWTH | CS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 3 | 4 | 3 | 3 | 3 | 4 | 3 | 4 |
| B | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| C | 3 | 3 | 3 | 4 | 3 | 3 | 3 | 3 |
| D | 4 | 3 | 4 | 4 | 4 | 5 | 5 | 5 |
| E | 3 | 4 | 3 | 4 | 3 | 4 | 3 | 4 |

### Producto, tecnología y datos

| Alt. | CTO | UX | PROD | FE | BE | DATA | QA |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 5 | 3 | 3 | 5 | 5 | 5 | 5 |
| B | 4 | 5 | 5 | 4 | 4 | 5 | 5 |
| C | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| D | 3 | 5 | 4 | 3 | 3 | 3 | 3 |
| E | 4 | 4 | 3 | 4 | 4 | 5 | 4 |

### Inteligencia, operación y recuperación

| Alt. | COpO | SHARK | TG | SENT | AP | CI | OPS | REC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 5 | 3 | 3 | 5 | 4 | 4 | 5 | 5 |
| B | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| C | 3 | 5 | 3 | 3 | 4 | 4 | 3 | 3 |
| D | 3 | 4 | 5 | 3 | 4 | 5 | 3 | 3 |
| E | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |

## 10.8 Decisión de Team Center

**Elegida: Alternativa B, Pulso de equipo.**

El Team Center debe comenzar por el estado presente y abrir profundidad de forma progresiva. El perfil A, el laboratorio C, el seguimiento D y el archivo E sobreviven como capacidades subordinadas, no como modelos de experiencia independientes.

El pulso nunca se calcula como una puntuación opaca. Es una composición editorial de hechos confirmados, cambios y limitaciones.

# 11. Experiencia de seguir una competición: Competition Center

## 11.1 Resultado que debe producir

El usuario debe comprender qué está en juego, dónde se encuentra la competición y qué jornada o trayectoria merece atención.

## 11.2 Alternativa A: Clasificación primero

**Concepto:** tabla, posiciones, diferencias y acceso a cada equipo como eje.

- **Ventajas:** modelo mental conocido y respuesta rápida a “cómo van”.
- **Desventajas:** la tabla no explica por sí sola el momento de la competición.
- **Complejidad:** baja/media.
- **Escalabilidad:** alta.
- **Valor usuario:** consulta directa.
- **Valor empresa:** cobertura eficiente.
- **Valor SHARK:** contexto posicional, pero poca narrativa.
- **Valor Telegram:** cambios de posición y cierre de jornada.
- **Valor móvil:** medio por tablas.
- **Valor desktop:** alto.
- **Riesgo principal:** desempates o fases incompletas mal representadas.

## 11.3 Alternativa B: Centro de jornada

**Concepto:** cada jornada concentra partidos, clasificación antes/después, historias y siguientes fechas.

- **Ventajas:** conecta calendario y consecuencias.
- **Desventajas:** pierde perspectiva entre jornadas y fases largas.
- **Complejidad:** media.
- **Escalabilidad:** alta.
- **Valor usuario:** entiende el bloque competitivo actual.
- **Valor empresa:** recurrencia semanal.
- **Valor SHARK:** contexto directo para cada partido.
- **Valor Telegram:** resumen y alertas de jornada.
- **Valor móvil:** alto.
- **Valor desktop:** alto.
- **Riesgo principal:** competiciones sin jornadas regulares.

## 11.4 Alternativa C: Narrativa de temporada

**Concepto:** la competición se presenta como una historia verificable de fase, stakes, trayectorias, próxima jornada y cambios de posición.

- **Ventajas:** une tabla, calendario y significado sin reducirse a ninguno.
- **Desventajas:** requiere reglas distintas para liga, copa, grupos y eliminatorias.
- **Complejidad:** alta.
- **Escalabilidad:** alta cuando el modelo de formato está certificado.
- **Valor usuario:** entiende qué importa y por qué.
- **Valor empresa:** contenido recurrente y diferenciación editorial.
- **Valor SHARK:** interpreta stakes, forma y comparabilidad con contexto.
- **Valor Telegram:** envía cambios de fase o jornada con motivo.
- **Valor móvil:** alto con capítulos breves.
- **Valor desktop:** muy alto.
- **Riesgo principal:** aplicar una narrativa incorrecta a formatos no comprendidos.

## 11.5 Alternativa D: Laboratorio de competición

**Concepto:** tendencias agregadas, líderes, distribuciones y comparaciones por temporada.

- **Ventajas:** profundidad analítica y valor experto.
- **Desventajas:** exige cobertura completa y puede alejarse de la tarea cotidiana.
- **Complejidad:** muy alta.
- **Escalabilidad:** media.
- **Valor usuario:** alto para análisis, bajo para orientación rápida.
- **Valor empresa:** contenido ELITE y autoridad.
- **Valor SHARK:** alto con muestras suficientes.
- **Valor Telegram:** limitado a hallazgos excepcionales.
- **Valor móvil:** bajo/medio.
- **Valor desktop:** muy alto.
- **Riesgo principal:** sesgos por cobertura parcial.

## 11.6 Alternativa E: Lente personal de competición

**Concepto:** la misma competición se reorganiza alrededor de equipos, jugadores y partidos seguidos por el usuario.

- **Ventajas:** reduce ruido y conecta preferencias.
- **Desventajas:** puede ocultar la historia global.
- **Complejidad:** alta.
- **Escalabilidad:** alta.
- **Valor usuario:** relevancia personal.
- **Valor empresa:** retención y alertas.
- **Valor SHARK:** contextualiza intereses.
- **Valor Telegram:** muy alto.
- **Valor móvil:** muy alto.
- **Valor desktop:** alto.
- **Riesgo principal:** burbuja que impida comprender la competición.

## 11.7 Matriz de decisión: Competition Center

### Dirección, cliente y crecimiento

| Alt. | CEO | COO | CPO | CDO | CRO | CCO | GROWTH | CS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 3 | 5 | 3 | 3 | 3 | 4 | 3 | 4 |
| B | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| C | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| D | 3 | 3 | 3 | 4 | 3 | 3 | 3 | 3 |
| E | 4 | 3 | 4 | 4 | 4 | 5 | 5 | 5 |

### Producto, tecnología y datos

| Alt. | CTO | UX | PROD | FE | BE | DATA | QA |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 5 | 3 | 3 | 4 | 5 | 5 | 5 |
| B | 4 | 4 | 4 | 4 | 4 | 5 | 4 |
| C | 4 | 5 | 5 | 4 | 4 | 5 | 5 |
| D | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| E | 3 | 5 | 4 | 3 | 3 | 3 | 3 |

### Inteligencia, operación y recuperación

| Alt. | COpO | SHARK | TG | SENT | AP | CI | OPS | REC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 5 | 3 | 3 | 5 | 4 | 4 | 5 | 5 |
| B | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| C | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| D | 3 | 5 | 3 | 3 | 4 | 4 | 3 | 3 |
| E | 3 | 4 | 5 | 3 | 4 | 5 | 3 | 3 |

## 11.8 Decisión de Competition Center

**Elegida: Alternativa C, Narrativa de temporada.**

La competición debe explicar stakes y movimiento. La tabla y la jornada son evidencias dentro de la historia, no productos separados. La lente personal puede reducir ruido, pero nunca reemplaza el contexto global.

Cada formato competitivo necesita una definición certificada. Cuando no exista, la experiencia vuelve a tabla, calendario y resultados sin inventar una narrativa.

# 12. Experiencia de entender un jugador: Player Center

## 12.1 Resultado que debe producir

El usuario debe comprender disponibilidad, rol, forma contextual e impacto probable sin comparar posiciones incompatibles ni convertir una puntuación opaca en verdad.

## 12.2 Alternativa A: Perfil estadístico

**Concepto:** biografía deportiva, equipo, posición y métricas por competición y temporada.

- **Ventajas:** claro, completo y escalable con fuentes estructuradas.
- **Desventajas:** obliga a interpretar números y favorece comparaciones superficiales.
- **Complejidad:** media.
- **Escalabilidad:** alta cuando la cobertura existe.
- **Valor usuario:** referencia rápida.
- **Valor empresa:** amplitud de catálogo.
- **Valor SHARK:** materia prima, poca explicación.
- **Valor Telegram:** alertas básicas.
- **Valor móvil:** medio.
- **Valor desktop:** alto.
- **Riesgo principal:** volumen de métricas sin relevancia por rol.

## 12.3 Alternativa B: Lente de rol e impacto

**Concepto:** las métricas y comparaciones cambian según el rol real del jugador; disponibilidad, carga, participación y próximo contexto determinan la lectura.

- **Ventajas:** convierte estadísticas en comprensión y evita comparaciones incompatibles.
- **Desventajas:** exige taxonomía de roles, cobertura y metodología transparente.
- **Complejidad:** alta.
- **Escalabilidad:** media/alta por dependencia de datos.
- **Valor usuario:** entiende cómo y dónde influye el jugador.
- **Valor empresa:** diferenciación de calidad frente a perfiles genéricos.
- **Valor SHARK:** explica impacto sin inventar una nota universal.
- **Valor Telegram:** alerta cuando disponibilidad o rol cambian de forma confirmada.
- **Valor móvil:** alto por selección de pocas métricas relevantes.
- **Valor desktop:** muy alto.
- **Riesgo principal:** asignar un rol incorrecto o inferirlo con evidencia insuficiente.

## 12.4 Alternativa C: Línea de forma

**Concepto:** cada actuación forma una secuencia de minutos, rol, rival y contribución.

- **Ventajas:** comunica evolución y evita una media aislada.
- **Desventajas:** puede sobrevalorar muestras recientes.
- **Complejidad:** media/alta.
- **Escalabilidad:** alta con histórico completo.
- **Valor usuario:** comprende tendencia.
- **Valor empresa:** retorno y contenido antes de partidos.
- **Valor SHARK:** contextualiza cambios.
- **Valor Telegram:** avisos de cambio sostenido.
- **Valor móvil:** alto.
- **Valor desktop:** alto.
- **Riesgo principal:** narrar ruido como forma.

## 12.5 Alternativa D: Vigilancia de disponibilidad

**Concepto:** el centro prioriza lesiones, sanciones, convocatorias, minutos y probabilidad operativa de participación, sin inferir titularidad.

- **Ventajas:** responde una pregunta de gran utilidad antes del partido.
- **Desventajas:** demasiado estrecho como experiencia completa.
- **Complejidad:** alta por fuentes y cambios.
- **Escalabilidad:** baja/media.
- **Valor usuario:** alta utilidad puntual.
- **Valor empresa:** alertas valiosas.
- **Valor SHARK:** evita análisis basados en jugadores ausentes.
- **Valor Telegram:** muy alto.
- **Valor móvil:** muy alto.
- **Valor desktop:** medio.
- **Riesgo principal:** publicar rumores o estados desactualizados.

## 12.6 Alternativa E: Historia de carrera

**Concepto:** trayectoria por clubes, competiciones, roles, hitos y evolución.

- **Ventajas:** contexto humano y memoria duradera.
- **Desventajas:** valor menor para la decisión del día.
- **Complejidad:** media/alta.
- **Escalabilidad:** media.
- **Valor usuario:** profundidad y descubrimiento.
- **Valor empresa:** contenido durable y buscable.
- **Valor SHARK:** contexto histórico limitado.
- **Valor Telegram:** bajo salvo hitos.
- **Valor móvil:** medio.
- **Valor desktop:** alto.
- **Riesgo principal:** histórico incompleto o narrativa excesiva.

## 12.7 Matriz de decisión: Player Center

### Dirección, cliente y crecimiento

| Alt. | CEO | COO | CPO | CDO | CRO | CCO | GROWTH | CS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 3 | 4 | 3 | 3 | 3 | 4 | 3 | 4 |
| B | 5 | 4 | 5 | 5 | 4 | 5 | 5 | 5 |
| C | 4 | 4 | 4 | 5 | 4 | 4 | 4 | 4 |
| D | 4 | 3 | 4 | 4 | 4 | 5 | 4 | 5 |
| E | 3 | 4 | 3 | 4 | 3 | 4 | 3 | 4 |

### Producto, tecnología y datos

| Alt. | CTO | UX | PROD | FE | BE | DATA | QA |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 5 | 3 | 3 | 5 | 5 | 5 | 5 |
| B | 4 | 5 | 5 | 4 | 4 | 4 | 4 |
| C | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| D | 3 | 4 | 4 | 4 | 3 | 3 | 3 |
| E | 4 | 4 | 3 | 4 | 4 | 4 | 4 |

### Inteligencia, operación y recuperación

| Alt. | COpO | SHARK | TG | SENT | AP | CI | OPS | REC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 5 | 3 | 3 | 5 | 4 | 4 | 5 | 5 |
| B | 4 | 5 | 5 | 4 | 5 | 5 | 4 | 4 |
| C | 4 | 5 | 4 | 4 | 4 | 5 | 4 | 4 |
| D | 3 | 5 | 5 | 3 | 4 | 4 | 3 | 3 |
| E | 4 | 3 | 3 | 4 | 4 | 4 | 4 | 4 |

## 12.8 Decisión de Player Center

**Elegida: Alternativa B, Lente de rol e impacto.**

NeMeSiS no necesita otra ficha de estadísticas. Debe seleccionar información según rol, rival, competición y disponibilidad. La línea de forma C complementa la lectura; la vigilancia D se activa solo con fuentes confirmadas.

Si el rol o la cobertura no pueden certificarse, el sistema presenta identidad, minutos y hechos disponibles. No inventa una lente avanzada.


# 13. Experiencia de vivir el directo: Live Center

## 13.1 Resultado que debe producir

El usuario debe sentir que el deporte está ocurriendo porque comprende cambios reales, no porque la interfaz parpadea. Debe saber qué cambió, cuándo, con qué frescura y si merece abrir el partido.

## 13.2 Alternativa A: Muro de marcadores

**Concepto:** máxima densidad de partidos, marcador, minuto y estado en una visión global.

- **Ventajas:** cobertura rápida y comparación simultánea.
- **Desventajas:** comunica resultado, pero no significado.
- **Complejidad:** baja/media.
- **Escalabilidad:** técnica alta; cognitiva baja en grandes jornadas.
- **Valor usuario:** vistazo inmediato.
- **Valor empresa:** amplia cobertura y bajo coste editorial.
- **Valor SHARK:** limitado; añadir análisis a todo genera ruido.
- **Valor Telegram:** enlaces simples a partidos.
- **Valor móvil:** medio/bajo.
- **Valor desktop:** alto.
- **Riesgo principal:** parecer vivo aunque los datos estén stale.

## 13.3 Alternativa B: Flujo de eventos

**Concepto:** una secuencia cronológica combina goles, tarjetas, cambios, descansos y finales.

- **Ventajas:** transmite movimiento y relación temporal.
- **Desventajas:** muchos eventos simultáneos saturan y desplazan lo importante.
- **Complejidad:** alta.
- **Escalabilidad:** media.
- **Valor usuario:** descubre qué acaba de pasar.
- **Valor empresa:** retorno y alertas.
- **Valor SHARK:** puede explicar eventos relevantes.
- **Valor Telegram:** cada evento tiene un objeto de mensaje natural.
- **Valor móvil:** alto en una sola columna.
- **Valor desktop:** medio/alto.
- **Riesgo principal:** convertir volumen en importancia.

## 13.4 Alternativa C: Radar de cambio

**Concepto:** la experiencia prioriza diferencias desde la última lectura: inicio, marcador, fase, hecho decisivo, cambio de dominio verificable, pick afectado o dato stale.

- **Ventajas:** reduce repetición y responde “qué cambió”.
- **Desventajas:** necesita memoria de lectura y reglas claras de relevancia.
- **Complejidad:** alta.
- **Escalabilidad:** alta si los cambios se calculan sobre snapshots canónicos.
- **Valor usuario:** vuelve y entiende la jornada en segundos.
- **Valor empresa:** retención basada en utilidad, no en refresco compulsivo.
- **Valor SHARK:** explica únicamente cambios sostenidos por evidencia.
- **Valor Telegram:** envía los mismos cambios con dedupe y preferencias.
- **Valor móvil:** muy alto.
- **Valor desktop:** muy alto al combinar resumen y foco.
- **Riesgo principal:** declarar cambio cuando solo cambió el proveedor o el formato.

## 13.5 Alternativa D: Sala live personal

**Concepto:** solo favoritos, picks seguidos y alertas elegidas forman la experiencia principal.

- **Ventajas:** muy relevante y silenciosa.
- **Desventajas:** elimina descubrimiento y aporta poco al usuario nuevo.
- **Complejidad:** alta.
- **Escalabilidad:** alta con preferencias fiables.
- **Valor usuario:** seguimiento sin ruido.
- **Valor empresa:** retención y conexión de cuenta.
- **Valor SHARK:** análisis concentrado.
- **Valor Telegram:** excelente.
- **Valor móvil:** muy alto.
- **Valor desktop:** alto.
- **Riesgo principal:** burbuja y dependencia de configuración previa.

## 13.6 Alternativa E: Mapa operativo del directo

**Concepto:** partidos organizados por fase, intensidad de cambio, cobertura y calidad del dato.

- **Ventajas:** visión potente de muchas competiciones y estado de la plataforma.
- **Desventajas:** mezcla interés deportivo con señales operativas.
- **Complejidad:** muy alta.
- **Escalabilidad:** alta para operadores; media para clientes.
- **Valor usuario:** útil para usuarios expertos.
- **Valor empresa:** gran visibilidad de cobertura.
- **Valor SHARK:** encuentra dónde existe evidencia suficiente.
- **Valor Telegram:** ayuda a priorizar candidatos.
- **Valor móvil:** bajo.
- **Valor desktop:** muy alto.
- **Riesgo principal:** exponer diagnóstico técnico al cliente.

## 13.7 Matriz de decisión: Live Center

### Dirección, cliente y crecimiento

| Alt. | CEO | COO | CPO | CDO | CRO | CCO | GROWTH | CS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 3 | 5 | 3 | 3 | 3 | 4 | 3 | 4 |
| B | 4 | 3 | 4 | 5 | 4 | 4 | 4 | 4 |
| C | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| D | 4 | 3 | 4 | 4 | 4 | 5 | 5 | 5 |
| E | 3 | 4 | 3 | 4 | 3 | 3 | 3 | 3 |

### Producto, tecnología y datos

| Alt. | CTO | UX | PROD | FE | BE | DATA | QA |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 5 | 3 | 3 | 5 | 5 | 5 | 5 |
| B | 3 | 4 | 4 | 3 | 3 | 4 | 3 |
| C | 4 | 5 | 5 | 4 | 4 | 5 | 5 |
| D | 3 | 5 | 4 | 3 | 3 | 3 | 3 |
| E | 3 | 3 | 3 | 3 | 3 | 5 | 4 |

### Inteligencia, operación y recuperación

| Alt. | COpO | SHARK | TG | SENT | AP | CI | OPS | REC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 5 | 3 | 4 | 5 | 4 | 4 | 5 | 5 |
| B | 3 | 4 | 5 | 3 | 4 | 4 | 3 | 3 |
| C | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| D | 3 | 4 | 5 | 3 | 4 | 5 | 3 | 3 |
| E | 5 | 4 | 4 | 5 | 5 | 5 | 5 | 5 |

## 13.8 Decisión de Live Center

**Elegida: Alternativa C, Radar de cambio.**

Live debe conservar una lista completa accesible, pero su experiencia principal es el cambio verificable. El muro A aporta cobertura; el flujo B aporta hechos; la sala D personaliza. El mapa E pertenece al admin, no al cliente.

Cuando la frescura caduca, el radar deja de inferir, conserva la última lectura como stale y explica el límite.

# 14. Experiencia de volver cada día: Sports Hub

## 14.1 Resultado que debe producir

Sports Hub debe responder en una sola visita:

- qué cambió desde ayer;
- qué ocurre hoy;
- qué merece atención ahora;
- qué sigo personalmente;
- qué acción tiene sentido;
- qué puedo ignorar con tranquilidad.

## 14.2 Alternativa A: Dashboard universal

**Concepto:** todos los módulos principales aparecen como bloques simultáneos.

- **Ventajas:** cobertura visible y acceso directo.
- **Desventajas:** cada módulo compite por atención y la página envejece como panel.
- **Complejidad:** media.
- **Escalabilidad:** baja a medida que crece el producto.
- **Valor usuario:** panorama completo.
- **Valor empresa:** exposición de todas las capacidades.
- **Valor SHARK:** una tarjeta más entre muchas.
- **Valor Telegram:** estado del canal visible.
- **Valor móvil:** bajo.
- **Valor desktop:** alto si el número de módulos es limitado.
- **Riesgo principal:** mostrar módulos porque existen, no porque importan.

## 14.3 Alternativa B: Feed personalizado continuo

**Concepto:** una secuencia aprende de favoritos, sesiones y acciones consentidas.

- **Ventajas:** alta relevancia y descubrimiento sin navegación rígida.
- **Desventajas:** opacidad, repetición, scroll infinito y dependencia de señal conductual.
- **Complejidad:** muy alta.
- **Escalabilidad:** técnica alta; gobernanza compleja.
- **Valor usuario:** experiencia individual.
- **Valor empresa:** retención y descubrimiento comercial.
- **Valor SHARK:** puede contextualizar cada elemento.
- **Valor Telegram:** aprende afinidades de canal.
- **Valor móvil:** alto.
- **Valor desktop:** medio.
- **Riesgo principal:** optimizar engagement en vez de utilidad o bienestar.

## 14.4 Alternativa C: Briefing deportivo de hoy

**Concepto:** una narración finita y ordenada prepara al usuario: cambios, agenda, atención, seguimiento personal, decisión responsable y siguiente acción.

- **Ventajas:** claridad, cierre, confianza y utilidad incluso cuando no hay picks o live.
- **Desventajas:** requiere reglas editoriales que decidan qué queda fuera del briefing.
- **Complejidad:** alta.
- **Escalabilidad:** alta si resume por significado y permite profundizar.
- **Valor usuario:** sabe qué necesita sin recorrer todo el producto.
- **Valor empresa:** hábito diario, propuesta de valor y conversión contextual responsable.
- **Valor SHARK:** actúa como director del briefing, incluso para recomendar esperar.
- **Valor Telegram:** entrega el resumen o cambio elegido y devuelve al mismo contexto.
- **Valor móvil:** muy alto.
- **Valor desktop:** muy alto.
- **Riesgo principal:** confundir una prioridad editorial con una verdad deportiva.

## 14.5 Alternativa D: Centro de búsqueda y comandos

**Concepto:** una entrada principal permite buscar entidad o expresar una tarea: “partidos de hoy”, “mi equipo”, “con pick”, “qué cambió”.

- **Ventajas:** extraordinariamente rápido para usuarios con intención.
- **Desventajas:** débil para descubrimiento, onboarding y usuarios que no saben qué preguntar.
- **Complejidad:** alta.
- **Escalabilidad:** alta con taxonomía y búsqueda robustas.
- **Valor usuario:** acceso directo.
- **Valor empresa:** reduce fricción y revela intenciones.
- **Valor SHARK:** responde preguntas concretas.
- **Valor Telegram:** configura seguimiento mediante acciones explícitas.
- **Valor móvil:** alto.
- **Valor desktop:** muy alto.
- **Riesgo principal:** hacer depender toda la experiencia de lenguaje o búsqueda perfecta.

## 14.6 Alternativa E: Mapa deportivo global

**Concepto:** la exploración parte del mundo, país, competición y entidades activas.

- **Ventajas:** descubrimiento visual y sensación de cobertura.
- **Desventajas:** prioriza geografía sobre tareas y añade distancia al contenido.
- **Complejidad:** alta.
- **Escalabilidad:** alta con metadatos consistentes.
- **Valor usuario:** exploración amplia.
- **Valor empresa:** comunica alcance.
- **Valor SHARK:** contexto geográfico limitado.
- **Valor Telegram:** configuración por región o competición.
- **Valor móvil:** medio/bajo.
- **Valor desktop:** alto.
- **Riesgo principal:** convertir cobertura en espectáculo sin utilidad diaria.

## 14.7 Matriz de decisión: Sports Hub

### Dirección, cliente y crecimiento

| Alt. | CEO | COO | CPO | CDO | CRO | CCO | GROWTH | CS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 3 | 4 | 3 | 3 | 4 | 3 | 4 | 3 |
| B | 4 | 2 | 4 | 4 | 5 | 4 | 5 | 4 |
| C | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| D | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| E | 3 | 3 | 3 | 5 | 3 | 3 | 4 | 3 |

### Producto, tecnología y datos

| Alt. | CTO | UX | PROD | FE | BE | DATA | QA |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 4 | 3 | 3 | 4 | 4 | 4 | 4 |
| B | 2 | 4 | 4 | 3 | 2 | 2 | 2 |
| C | 4 | 5 | 5 | 4 | 4 | 5 | 5 |
| D | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| E | 3 | 3 | 3 | 3 | 3 | 4 | 3 |

### Inteligencia, operación y recuperación

| Alt. | COpO | SHARK | TG | SENT | AP | CI | OPS | REC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 4 | 3 | 3 | 4 | 4 | 4 | 4 | 4 |
| B | 2 | 4 | 4 | 2 | 3 | 5 | 2 | 2 |
| C | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| D | 4 | 5 | 4 | 4 | 4 | 4 | 4 | 4 |
| E | 3 | 3 | 3 | 3 | 3 | 4 | 3 | 3 |

## 14.8 Decisión de Sports Hub

**Elegida: Alternativa C, Briefing deportivo de hoy.**

El Sports Hub no es un dashboard ni un feed infinito. Es una sesión finita que prepara al usuario y le deja una siguiente acción clara. La búsqueda D permanece disponible como acelerador; el mapa E vive como exploración secundaria.

El briefing debe poder ser breve o incluso concluir “sin cambios relevantes”. No rellena espacio ni fuerza una recomendación.


# 15. Decisión integrada del Product Board

## 15.1 Portafolio elegido

| Experiencia | Alternativa elegida | Decisión |
|---|---|---|
| Calendario | E. Historia del día por capas | Cobertura completa con contexto, intención y posición preservados |
| Match Center | D. Historia viva por ciclo | Una única historia antes, durante y después |
| Team Center | B. Pulso de equipo | Estado actual, cambio y siguiente reto antes que archivo |
| Competition Center | C. Narrativa de temporada | Stakes, trayectoria y jornada dentro del mismo relato |
| Player Center | B. Lente de rol e impacto | Métricas relevantes por rol, disponibilidad y contexto |
| Live Center | C. Radar de cambio | Cambios verificables en lugar de movimiento decorativo |
| Sports Hub | C. Briefing deportivo de hoy | Una sesión finita que prepara y orienta |

## 15.2 Por qué esta combinación es un producto

Las alternativas elegidas comparten cinco decisiones:

1. **El tiempo importa.** Todas distinguen qué era cierto antes, qué cambió y qué sigue.
2. **La entidad conserva identidad.** El mismo partido, equipo, jugador o competición no se reconstruye en cada ruta.
3. **La profundidad llega después de la orientación.** Primero se responde la pregunta; después se abre evidencia.
4. **La atención es explicable.** Una prioridad siempre puede justificar fuente, frescura y limitación.
5. **El usuario controla continuidad y canal.** Favoritos, alertas, Telegram y personalización son opt-in y reversibles.

La visión no es la alternativa más fácil. Exige contratos de lifecycle, contexto y entidades más rigurosos que un dashboard o una lista. Se elige porque ofrece una razón propia para preferir NeMeSiS.

## 15.3 Veredicto de cada especialista

| Rol | Veredicto |
|---|---|
| CEO | La propuesta es diferenciable porque convierte cobertura en criterio |
| COO | Es operable si cada experiencia tiene modo degradado y responsable |
| CTO | Debe construirse por contratos compartidos y etapas, nunca como siete silos |
| CPO | El Sports Experience Loop ofrece una promesa coherente de principio a fin |
| CDO | La jerarquía debe comunicar tiempo, cambio y confianza antes que decoración |
| Chief Operations Officer | Cada prioridad necesita trazabilidad y una siguiente acción operativa |
| CRO | El valor pagado debe ser profundidad y continuidad, no hechos secuestrados |
| CCO | El mayor activo comercial es poder decir “no hay evidencia suficiente” |
| UX | La visión sigue siendo hipótesis hasta medir tareas con usuarios |
| Producto | Cada centro tiene una responsabilidad única y evita duplicación |
| Frontend | Móvil y desktop requieren composición propia, no dos jerarquías distintas |
| Backend | Identidad, lifecycle, frescura y contexto deben compartir contratos |
| SHARK | La inteligencia entra por preguntas concretas y puede recomendar esperar |
| Telegram | El canal entrega cambios elegidos y siempre devuelve al contexto |
| Datos deportivos | Ninguna narrativa puede superar la cobertura certificada |
| QA | Cada estado debe probarse con datos completos, vacíos, stale y bloqueados |
| Sentinel | Debe vigilar contratos, duplicación, contexto, stale y navegación |
| AutoPilot | Puede detectar y proponer; no debe implementar ni publicar |
| Company Intelligence | Medirá utilidad agregada sin confundir actividad con valor |
| Operations Center | Debe exponer salud del circuito sin filtrar diagnóstico al cliente |
| Recovery | Cada experiencia necesita fallback, continuidad y restauración de contexto |
| Growth | El hábito debe nacer de utilidad diaria, no de feed infinito |
| Customer Success | El usuario debe entender qué recibe, qué falta y qué puede hacer |

# 16. Arquitectura de experiencia

## 16.1 El recorrido principal

```text
Sports Hub: “qué merece atención”
  → Calendario: “qué existe y cómo lo encuentro”
    → Match Center: “qué ocurre en este partido”
      → Team / Competition / Player: “qué contexto lo explica”
        → Live Center: “qué cambió ahora”
          → Match Center final: “qué ocurrió y qué aprendimos”
            → Sports Hub siguiente: “qué cambió desde mi última visita”
```

El usuario puede entrar por cualquier entidad, búsqueda o enlace Telegram. El producto reconstruye el mismo contexto sin obligarlo a volver a Inicio.

## 16.2 Contexto que siempre viaja

Cuando siga siendo válido, el recorrido conserva:

- fecha y hora Madrid;
- competición y fase;
- entidad de origen;
- filtros activos;
- posición o grupo de la colección;
- favorito y alertas;
- estado de frescura;
- última lectura del usuario;
- membresía aplicable;
- destino de retorno.

No se conserva contexto stale, incompatible o sensible sin explicarlo.

## 16.3 Navegación definitiva

### Desktop

- Destinos primarios: Sports Hub, Partidos, Live, Picks y SHARK.
- Acceso global a búsqueda.
- Destinos secundarios: Histórico, Telegram, Favoritos y Cuenta.
- Centros de entidad conectados mediante nombres y breadcrumbs solo cuando existe profundidad real.
- Contexto local disponible sin crear una segunda barra de navegación completa.

### Tablet

- Prioridad a contenido, contexto y búsqueda.
- Navegación compacta.
- Paneles secundarios pasan a superficies temporales o secuencia vertical.
- No se permiten tablas cuya única solución sea scroll horizontal permanente.

### Móvil

- Bottom nav estable con cinco destinos esenciales.
- Header compacto para búsqueda, alertas y cuenta.
- Filtros en una superficie temporal con resumen visible al cerrarla.
- Acción primaria al alcance de una mano.
- Retorno, posición, teclado y safe area preservados.
- Ninguna capa sticky puede consumir una parte desproporcionada del viewport.

## 16.4 Buscador y favoritos

El buscador no es una pantalla aislada. Es un acelerador universal para:

- partidos;
- equipos;
- jugadores;
- competiciones;
- picks propios;
- acciones deportivas.

Favoritos no significa “poner una estrella”. Significa:

- seguir una entidad;
- decidir qué cambios importan;
- elegir canal y frecuencia;
- construir un briefing personal;
- poder pausar o borrar ese seguimiento.

# 17. Cómo debe sentirse NeMeSiS

## 17.1 Calendario

Debe sentirse **amplio pero orientado**. El usuario percibe que la cobertura está completa sin cargar todo en su memoria. Sabe dónde está, por qué ve cada partido y cómo cambiar de intención.

No debe sentirse como:

- una lista infinita;
- un catálogo de ligas;
- una suma de filtros;
- un escaparate de picks.

## 17.2 Match Center

Debe sentirse **continuo y vivo**. La identidad no cambia; cambia la prioridad de la historia. El usuario sabe si el siguiente dato relevante será una alineación, el inicio, una actualización live o la liquidación final.

No debe sentirse como:

- pestañas sin relación;
- un casino;
- un informe congelado;
- varias pantallas pegadas.

## 17.3 Team Center

Debe sentirse **familiar y actual**. Explica el pulso del equipo sin pretender resumirlo en una nota.

No debe sentirse como:

- una enciclopedia;
- una tabla de estadísticas;
- un muro de noticias;
- una colección de rumores.

## 17.4 Competition Center

Debe sentirse **como una temporada con stakes**. Clasificación, jornada y calendario explican una misma evolución.

No debe sentirse como:

- una tabla aislada;
- un listado de jornadas;
- una historia inventada sobre formato incompleto.

## 17.5 Player Center

Debe sentirse **contextual y respetuoso**. El jugador se entiende por rol, disponibilidad y contribución, no por una cifra universal.

No debe sentirse como:

- una carta de videojuego;
- un ranking entre posiciones incompatibles;
- una fuente de rumores personales.

## 17.6 Live Center

Debe sentirse **vivo, sereno y verificable**. La tensión proviene del deporte real, no de animaciones o colores.

No debe sentirse como:

- una máquina de refresco;
- una alarma constante;
- una promesa de actualidad cuando el dato está stale.

## 17.7 SHARK

Debe sentirse **como un director deportivo prudente**:

- escucha una pregunta;
- declara qué evidencia tiene;
- separa dato e interpretación;
- presenta razones y contraargumentos;
- señala invalidadores;
- dice cuándo esperar;
- recuerda qué ocurrió después.

No debe sentirse como un chatbot genérico, una predicción automática ni un vendedor.

## 17.8 Telegram

Debe sentirse **como NeMeSiS fuera de NeMeSiS**:

- mismo lenguaje;
- misma calidad;
- misma prudencia;
- mismo estado;
- enlace al contexto exacto;
- frecuencia elegida.

No debe sentirse como spam, canal promocional o sustituto del producto.

## 17.9 Usuario

Debe sentirse:

- informado antes que estimulado;
- acompañado antes que dirigido;
- capaz de profundizar;
- seguro al ignorar contenido irrelevante;
- libre para pausar alertas, personalización y bankroll;
- respetado cuando no existen datos.

## 17.10 Admin

Debe sentirse **como un centro de operaciones**. En diez segundos debe saber:

- qué está sano;
- qué está degradado;
- qué afecta al cliente;
- qué evidencia existe;
- qué requiere aprobación;
- cuál es la siguiente acción.

El admin no replica la interfaz cliente ni expone una colección de herramientas sin prioridad.

## 17.11 Empresa

Debe sentirse **auditable y recuperable**:

- cada señal tiene fuente;
- cada decisión tiene propietario;
- cada automatización tiene límite;
- cada incidente tiene evidencia;
- cada release tiene rollback;
- cada aprendizaje distingue resultado de hipótesis.

# 18. Contratos de experiencia

## 18.1 Contrato de atención

Todo elemento prioritario debe responder:

1. Qué cambió.
2. Por qué importa.
3. Qué evidencia lo sostiene.
4. Qué limitación existe.
5. Qué puede hacer el usuario.
6. Cuándo conviene volver.

Si no puede responder, no merece una prioridad especial.

## 18.2 Contrato de identidad

Partido, equipo, jugador y competición deben conservar:

- identificador estable;
- nombre normalizado;
- fuente;
- cobertura;
- relaciones;
- estado de seguimiento;
- fallback honesto.

La ausencia de logo o escudo nunca crea una entidad distinta.

## 18.3 Contrato de lifecycle

El partido solo puede progresar mediante evidencia:

```text
PROGRAMADO
→ PRÓXIMO
→ LIVE CONFIRMADO
→ DESCANSO
→ LIVE CONFIRMADO
→ FINAL PENDIENTE DE VERIFICACIÓN
→ FINAL VERIFICADO
```

Estados aplazado, cancelado, suspendido, desconocido y stale interrumpen el flujo y se presentan explícitamente. Nunca se infiere un final por silencio del proveedor.

## 18.4 Contrato de frescura

Cada dato cuyo valor cambia con el tiempo debe conocer:

- timestamp;
- fuente;
- frescura;
- última confirmación;
- comportamiento al caducar.

El cliente recibe lenguaje humano. Admin recibe diagnóstico y motivo de exclusión.

## 18.5 Contrato de confianza

El Índice de Confianza mide calidad del dato:

- completitud;
- frescura;
- coherencia;
- fuente;
- verificabilidad.

Nunca mide:

- probabilidad de ganar;
- probabilidad de un resultado;
- rentabilidad;
- valor emocional;
- urgencia para apostar.

## 18.6 Contrato de vacío

Un estado vacío debe explicar:

- qué no existe;
- por qué puede ocurrir;
- qué sí está disponible;
- cuándo podría cambiar;
- qué acción es útil ahora.

No debe:

- mostrar ceros como métrica real cuando falta muestra;
- culpabilizar al usuario;
- rellenar con contenido no relacionado;
- esconder una degradación.

## 18.7 Contrato de retorno

Al volver desde una entidad:

- se restaura el contexto válido;
- no se reinicia el scroll por polling;
- se destaca brevemente el elemento de retorno sin animación invasiva;
- se informa si el conjunto cambió;
- se ofrece recuperar o descartar filtros stale.

# 19. SHARK como capa de criterio

## 19.1 Presencia

SHARK aparece solo en tres formas:

1. **Señal de atención breve:** indica que algo cambió o falta.
2. **Explicación contextual:** responde una pregunta dentro de una entidad.
3. **Director deportivo:** permite explorar razonamiento completo en su espacio.

No aparece como una tarjeta decorativa repetida.

## 19.2 Respuesta canónica

Toda lectura SHARK debe separar:

- pregunta;
- evidencia;
- interpretación;
- razones a favor;
- contraargumentos;
- invalidadores;
- limitaciones;
- recomendación: actuar, seguir, esperar o ignorar;
- próxima revisión.

## 19.3 Aprendizaje

SHARK puede:

- observar resultados cerrados;
- detectar patrones con muestra;
- recomendar una revisión;
- registrar calibración y limitaciones.

SHARK no puede:

- cambiar pesos automáticamente;
- publicar picks;
- elevar stake;
- ocultar segmentos perdedores;
- convertir correlación en causa.

# 20. Telegram como continuidad

## 20.1 Motivos válidos de mensaje

- cambio elegido por el usuario;
- alineación confirmada;
- inicio, descanso o final;
- pick publicado que supera el pipeline;
- cambio material de cuota con frescura válida;
- invalidación de una lectura;
- resultado y cierre;
- resumen diario solicitado.

## 20.2 Motivos inválidos

- rellenar una frecuencia;
- crear urgencia;
- repetir lo que el usuario ya recibió;
- promocionar un pick incompleto;
- declarar aperturas o conversiones no medibles;
- enviar por pertenecer a un plan.

## 20.3 Relación con membresía

- **FREE:** hechos útiles, seguimiento básico y existencia de análisis sin revelar una selección premium.
- **PRO:** mercado, selección, cuota registrada, riesgo, motivo y contraargumento cuando el pipeline lo permite.
- **ELITE y ELITE+:** escenarios, seguimiento y lectura avanzada solo con evidencia.

La membresía nunca rebaja el umbral de calidad.

# 21. Picks y Bankroll dentro del deporte

## 21.1 Pick

El pick vive dentro del partido y de su lifecycle. Debe explicar:

- por qué existe;
- mercado y selección;
- cuota y frescura;
- riesgo;
- stake orientativo;
- qué puede invalidarlo;
- cuándo se revisó;
- estado;
- resultado y aprendizaje.

No es el centro de toda entidad.

## 21.2 Bankroll

Bankroll ayuda a controlar:

- unidades;
- exposición;
- concentración;
- rachas;
- límites;
- pausa.

No mueve dinero, no ejecuta apuestas, no aumenta stake y no recomienda recuperar pérdidas.

# 22. Valor comercial sin degradar la experiencia

## 22.1 FREE

Debe permitir:

- entender qué ocurre;
- encontrar partidos;
- consultar resultados y estados reales;
- seguir una cantidad razonable de entidades;
- recibir utilidad básica;
- comprender por qué falta una recomendación.

La reacción buscada es: “Incluso gratis, NeMeSiS me ayuda a decidir qué mirar”.

## 22.2 PRO

Amplía:

- explicaciones SHARK;
- picks que superan el pipeline;
- razones, riesgos e invalidadores;
- alertas y Telegram contextual;
- seguimiento más profundo;
- histórico evaluable.

La reacción buscada es: “Tomo decisiones más informadas y pierdo menos tiempo”.

## 22.3 ELITE y ELITE+

Amplían:

- escenarios;
- seguimiento avanzado;
- comparaciones certificadas;
- gestión responsable de exposición;
- análisis más profundo cuando existe muestra;
- soporte y control de preferencias.

La reacción buscada es: “Tengo el máximo contexto disponible sin falsa certeza”.

## 22.4 Prohibiciones comerciales

- No bloquear hechos básicos.
- No inventar urgencia.
- No prometer beneficios.
- No diseñar empty states como castigo.
- No usar SHARK para presionar upgrade.
- No atribuir conversión sin evidencia persistida.

# 23. Operación, Company Intelligence y Recovery

## 23.1 Qué observa la empresa

Solo con señales reales y agregadas:

- tiempo hasta encontrar una entidad;
- búsquedas sin resultado;
- cambios de filtro;
- retrocesos;
- retorno desde Match Center;
- cobertura y frescura;
- estados stale;
- errores y fallos de navegación;
- alertas configuradas, bloqueadas y duplicadas;
- uso de SHARK;
- salida hacia otra fuente solo si se mide con consentimiento y método válido.

## 23.2 Qué no puede inferir

- satisfacción por duración de sesión;
- conversión por simple correlación;
- intención de apostar;
- preferencia emocional;
- calidad de una experiencia por número de clics;
- aprendizaje efectivo con muestra insuficiente.

## 23.3 Qué ve Operations Center

- salud por experiencia;
- cobertura y degradación;
- lifecycle incoherente;
- contratos rotos;
- stale e incompletos excluidos;
- errores de búsqueda;
- fallos de Telegram;
- impacto cliente;
- siguiente acción y propietario.

## 23.4 Recovery

Cada experiencia debe tener:

- estado degradado;
- fallback de última información confirmada;
- aviso de frescura;
- navegación funcional sin proveedor;
- retorno seguro;
- criterio de recuperación;
- evidencia de cierre.

Recovery Simulator prueba escenarios sin dañar producción.

# 24. Sistema de calidad permanente

## 24.1 Sentinel

Sentinel debe detectar:

- consumidores que recalculan métricas;
- estados lifecycle imposibles;
- live sin evidencia;
- contexto que se pierde al volver;
- navegación duplicada;
- mezcla cliente/admin;
- tarjetas fuera de contrato;
- texto técnico en cliente;
- prioridad sin evidencia;
- filtros que ocultan partidos sin explicación;
- Telegram sin dedupe;
- SHARK sin limitaciones;
- empty states con cifras inventadas.

## 24.2 AutoPilot

AutoPilot puede:

- abrir una incidencia;
- reunir evidencia;
- identificar consumidores probables;
- proponer criterios de aceptación;
- generar un prompt;
- pedir aprobación.

No puede modificar experiencia, datos, código, mensajes o producción.

## 24.3 QA de experiencia

Cada cambio futuro debe cubrir:

- desktop;
- tablet;
- móvil;
- teclado;
- lector de pantalla;
- zoom;
- reduced motion;
- colección pequeña;
- colección grande;
- dato completo;
- dato incompleto;
- dato stale;
- proveedor caído;
- usuario nuevo;
- usuario con favoritos;
- FREE, PRO y ELITE;
- ida y vuelta entre entidades.

# 25. Medición de éxito

## 25.1 Métrica norte

**Tarea deportiva resuelta con contexto y confianza.**

Una tarea está resuelta cuando el usuario:

1. encuentra la entidad o situación;
2. comprende su estado;
3. identifica qué cambió;
4. sabe la limitación relevante;
5. completa o descarta una siguiente acción.

No existe todavía un valor baseline certificado para esta métrica.

## 25.2 Métricas por experiencia

| Experiencia | Señales a medir | Lo que no debe asumirse |
|---|---|---|
| Sports Hub | briefing completado, siguiente acción útil, retorno | más tiempo equivale a más valor |
| Calendario | éxito de búsqueda, tiempo hasta partido, retrocesos, filtros | scroll equivale a fracaso |
| Match Center | continuidad pre/live/post, retorno, comprensión de estado | más módulos equivalen a profundidad |
| Team Center | seguimiento, próximo partido abierto, cambio comprendido | favorito equivale a afición permanente |
| Competition Center | jornada y stakes comprendidos | tabla vista equivale a comprensión |
| Player Center | rol y disponibilidad comprendidos | comparación abierta equivale a utilidad |
| Live Center | cambio identificado, latencia, stale comprendido | refresco equivale a engagement sano |
| SHARK | pregunta resuelta, espera aceptada, limitación comprendida | respuesta larga equivale a calidad |
| Telegram | entrega, dedupe, retorno contextual | entregado equivale a leído |

## 25.3 Pruebas de preferencia

Para sostener que el usuario prefiere NeMeSiS se necesita:

- comparación de tareas, no de capturas;
- usuarios nuevos y recurrentes;
- desktop y móvil;
- días con pocos y muchos partidos;
- ausencia y presencia de live;
- seguimiento durante varias semanas;
- entrevista sobre confianza;
- medición consentida del cambio de aplicación;
- análisis de abandono sin atribución automática.

Hasta entonces, la superioridad es una hipótesis de diseño.

# 26. Roadmap definitivo

## Fase 0: Cerrar y medir la base

1. Cerrar P0, P1 y backlog P2 vigente.
2. Certificar Sports Data Contract, lifecycle y entidades.
3. Confirmar derechos, cobertura, costes y límites de proveedores.
4. Definir baseline de las tareas de PQV939-008.
5. Validar privacidad, analítica y juego responsable.

**Gate:** V939 estable, cero regresiones y evidencia suficiente para prototipar.

## Fase 1: Prototipos de experiencia

1. Prototipar al menos dos modelos de Calendario contra el baseline.
2. Prototipar Historia viva de Match Center en previo, live, final y stale.
3. Probar conservación de contexto.
4. Probar búsqueda y favoritos como aceleradores.
5. Validar móvil antes de elegir composición visual.

**Gate:** tareas mejoran sin ocultar cobertura ni degradar accesibilidad.

## Fase 2: Núcleo deportivo

1. Implementar la experiencia elegida de Calendario.
2. Implementar Match Center por lifecycle.
3. Implementar identidad y retorno entre entidades.
4. Consolidar búsqueda y favoritos.
5. Certificar rendimiento, datos y Browser QA.

**Gate:** Calendario y Match Center resuelven tareas completas con datos reales.

## Fase 3: Contexto de entidades

1. Team Center: Pulso de equipo.
2. Competition Center: Narrativa de temporada.
3. Player Center: Lente de rol solo donde exista cobertura.
4. Estados seguros para entidades incompletas.

**Gate:** ninguna narrativa supera la evidencia del proveedor.

## Fase 4: Tiempo real

1. Live Center: Radar de cambio.
2. Memoria de última lectura.
3. Alertas configurables y dedupe.
4. Telegram contextual.
5. QA de backoff, stale, polling y consumo.

**Gate:** cero falsos live, latencia aceptada y modo degradado certificado.

## Fase 5: Inteligencia y hábito

1. Sports Hub: Briefing deportivo de hoy.
2. SHARK contextual.
3. Picks dentro del lifecycle.
4. Bankroll voluntario.
5. Valor por membresía.

**Gate:** el briefing aporta valor incluso sin picks y SHARK puede recomendar esperar.

## Fase 6: Beta privada

1. Usuarios representativos y consentimiento.
2. Pruebas longitudinales.
3. Soporte e incidentes reales controlados.
4. Company Intelligence agregado.
5. Corrección de P0/P1 antes de ampliar.

**Gate:** preferencia, confianza y operación demostradas; no solo UI aprobada.

# 27. Decisiones descartadas como visión principal

| Alternativa | Motivo |
|---|---|
| Listas cronológicas como producto completo | Cobertura sin reducción de esfuerzo |
| Carriles como mundos separados | Riesgo de fragmentar una misma verdad |
| Personalización como portada única | Usuario nuevo sin valor y burbuja |
| Feed infinito | Optimiza consumo, no cierre de tarea |
| Dashboard universal | Módulos compiten por atención |
| Modo rápido y experto separados | Duplica producto y coherencia |
| Laboratorios de datos como entrada | Cobertura insuficiente y alta carga cognitiva |
| Picks como centro del partido | Reduce deporte a apuesta |
| Muro de marcadores como Live final | No explica cambios |
| Mapa operativo para cliente | Mezcla salud técnica y experiencia deportiva |

Descartado como visión principal no significa prohibido como módulo subordinado.

# 28. Preguntas que deben resolverse antes de implementar

1. ¿Qué contexto mínimo debe permanecer disponible en Calendario sin ocupar demasiado móvil?
2. ¿Qué reglas definen una prioridad de atención sin crear un score opaco?
3. ¿Cómo se modelan ligas, copas, grupos y eliminatorias con un contrato común?
4. ¿Qué roles de jugador pueden certificarse con la cobertura contratada?
5. ¿Cómo se mide “qué cambió” sin almacenar comportamiento sensible?
6. ¿Cuánto tiempo debe sobrevivir el contexto de retorno?
7. ¿Qué alertas aportan valor suficiente para justificar interrupción?
8. ¿Qué hechos básicos permanecen siempre FREE?
9. ¿Qué evidencia demuestra que PRO y ELITE ahorran esfuerzo o mejoran comprensión?
10. ¿Cómo se mide preferencia frente a otras aplicaciones sin tracking invasivo?
11. ¿Qué modo degradado se activa cuando falla cada proveedor?
12. ¿Qué coste operativo tiene ampliar una competición completa?

# 29. Supuestos y límites

- Las puntuaciones son un ejercicio de decisión interna, no investigación cuantitativa.
- No se ha probado ninguna alternativa con usuarios.
- No se afirma superioridad de mercado.
- No se afirma disponibilidad de todos los datos requeridos.
- Player Center avanzado depende de cobertura por rol.
- Live Center depende de evidencia y frescura certificadas.
- SHARK no tiene autorización para ejecutar decisiones.
- Telegram no puede enviar por volumen ni sin opt-in.
- Company Intelligence no puede convertir correlación en causalidad.
- La revisión legal por jurisdicción sigue pendiente antes de lanzamiento comercial.
- Esta Biblia no autoriza arquitectura, diseño visual ni implementación.

# 30. Decisión final

NeMeSiS debe convertirse en un **sistema de atención deportiva continuo, verificable y responsable**.

Su promesa no es:

> “Aquí están todos los datos”.

Su promesa es:

> “Aquí está lo que está ocurriendo, lo que cambió, lo que merece tu atención, la evidencia que lo sostiene y la siguiente decisión responsable”.

Un usuario debería preferir NeMeSiS porque:

1. encuentra antes;
2. entiende mejor;
3. conserva el contexto;
4. recibe menos ruido;
5. puede confiar en los límites;
6. sigue la misma historia en web y Telegram;
7. aprende del resultado sin falsa certeza.

Esta es la visión elegida por el Product Board. Su valor deberá demostrarse con prototipos, datos reales y beta privada antes de construirla como producto definitivo.

**Estado final de la Biblia:** `DECISION_COMPLETE / IMPLEMENTATION_NOT_AUTHORIZED`

