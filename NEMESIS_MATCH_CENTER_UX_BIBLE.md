# NeMeSiS Match Center UX Bible

## 0. Control del documento

**Proyecto de diseño:** V941 NEMESIS MATCH CENTER EXPERIENCE  
**Estado:** `DESIGN_STUDY / DECISION_PENDING / IMPLEMENTATION_NOT_AUTHORIZED`  
**Autoridad superior:** `NEMESIS_SPORTS_UX_BIBLE.md`  
**Código autorizado:** no  
**HTML, CSS o componentes autorizados:** no  
**Producción modificada:** no  
**Decisión entre alternativas:** pendiente  

V941 identifica este proyecto de diseño. No modifica la versión del runtime ni autoriza una release.

Este documento profundiza la experiencia Match Center sin modificar la visión aprobada:

- el usuario sigue el mismo partido antes, durante y después;
- el partido conserva una identidad estable;
- la prioridad cambia con el ciclo de vida y la evidencia;
- los hechos deportivos, la interpretación y las decisiones permanecen separados;
- ninguna ausencia se rellena con datos inventados;
- SHARK puede concluir que conviene esperar;
- Telegram extiende el contexto, no lo duplica;
- el partido nunca se reduce a una apuesta.

No se implementan ni se rediseñan Calendario, SHARK, Telegram o Sports Hub.

---

# 1. La pregunta principal

## Cuando un usuario pulsa un partido, ¿qué necesita durante los siguientes 20 minutos?

Necesita completar una secuencia humana, no recorrer una base de datos:

1. **Reconocer:** confirmar que ha abierto el partido correcto.
2. **Situarse:** saber estado, hora, marcador y qué está en juego.
3. **Detectar el cambio:** entender qué ocurrió desde la última lectura.
4. **Comprender:** identificar los hechos que explican el momento.
5. **Profundizar:** consultar contexto solo cuando resuelve una pregunta.
6. **Evaluar:** separar dato, interpretación, riesgo y decisión.
7. **Controlar:** decidir si seguir, guardar, recibir una alerta o salir.
8. **Continuar:** volver después sin reconstruir lo que ya había entendido.

La experiencia debe permitir una visita de diez segundos y una exploración de veinte minutos sin obligar a elegir entre dos productos distintos.

## 1.1 El resultado emocional

Al salir, el usuario debería sentir:

- sé exactamente qué está ocurriendo;
- entiendo qué cambió;
- conozco la calidad y los límites de la información;
- no he perdido tiempo con datos decorativos;
- puedo profundizar si lo necesito;
- no he recibido presión para apostar;
- sé cuál es la siguiente actualización relevante;
- puedo volver al mismo punto.

## 1.2 Lo que no debe sentir

- “Tengo muchos números, pero no sé qué significan”.
- “No sé si el marcador sigue actualizado”.
- “He visto tres veces la misma información”.
- “No encuentro la alineación o el último evento”.
- “SHARK está repitiendo los datos”.
- “El pick domina un partido que quizá no merece una decisión”.
- “Para seguirlo tengo que abrir otra aplicación”.
- “Al volver he perdido mi contexto”.

---

# 2. Evidencia, hipótesis y límites

## 2.1 Confirmado por la visión aprobada

- Match Center debe mantener una sola historia durante todo el ciclo.
- Los datos deportivos deben proceder del contrato canónico.
- Marcador, minuto, fase y eventos requieren evidencia y frescura válidas.
- La falta de cobertura debe producir un estado seguro.
- FREE conserva los hechos deportivos básicos.
- PRO y ELITE amplían criterio, escenarios y continuidad.
- SHARK no garantiza resultados ni ejecuta decisiones.
- Telegram requiere opt-in, dedupe, límites y un motivo de envío.
- Bankroll ayuda a controlar exposición y nunca mueve dinero.
- Cliente y admin no comparten información operativa ni navegación.

## 2.2 Hipótesis de experiencia

Estas hipótesis deben validarse antes de elegir una alternativa:

- el primer trabajo suele ser confirmar estado y marcador;
- “qué cambió” aporta más valor recurrente que repetir toda la ficha;
- la mayoría de usuarios no necesita todas las estadísticas en cada visita;
- la cronología es más útil durante live y postpartido que en una previa lejana;
- alineaciones y ausencias ganan prioridad cerca del inicio;
- clasificación, forma y H2H son contexto, no el centro permanente;
- una acción de seguimiento clara reduce la necesidad de mantener la sesión abierta;
- explicar por qué un dato no está disponible genera más confianza que ocultar el módulo;
- una lectura SHARK breve y contextual puede aportar más que un análisis siempre desplegado.

## 2.3 No medido

- orden real de consulta por segmento de usuario;
- tiempo hasta comprender el estado del partido;
- módulos ignorados de forma recurrente;
- profundidad media por fase;
- preferencia entre cronología, dossier o historia adaptativa;
- tolerancia a cambios de prioridad durante el ciclo;
- valor real de Telegram dentro del recorrido;
- impacto comercial por membresía;
- retención atribuible al Match Center;
- superioridad frente a otras aplicaciones.

No se tomarán hipótesis como hechos para justificar una implementación.

---

# 3. Los trabajos reales del usuario

## 3.1 Antes del partido

El usuario puede querer:

- confirmar fecha, hora Madrid, competición y jornada;
- entender qué se juega cada equipo;
- saber si las alineaciones están confirmadas;
- conocer ausencias verificadas;
- revisar forma, clasificación y enfrentamientos comparables;
- comprobar si existe pick y cuándo fue revisado;
- leer razones, riesgos e invalidadores;
- guardar el partido;
- configurar una alerta útil;
- decidir esperar a una nueva evidencia.

La experiencia no debe presentar el partido como live antes de tiempo ni convertir datos históricos en certeza futura.

## 3.2 Cerca del inicio

El usuario puede querer:

- confirmar que el partido comienza;
- detectar una alineación nueva o una ausencia relevante;
- saber qué cambió desde la previa;
- comprobar si una lectura o un pick sigue vigente;
- conocer la próxima actualización esperada;
- activar seguimiento sin configurar una cadena compleja de opciones.

La experiencia debe priorizar cambios verificados, no volver a mostrar toda la previa.

## 3.3 Durante el partido

El usuario puede querer:

- ver marcador, minuto o fase reales;
- identificar el último hecho importante;
- revisar la secuencia de eventos;
- comprender qué estadísticas explican el momento;
- consultar alineaciones, sustituciones y sanciones;
- comprobar el estado de un pick ya existente;
- entender si la hipótesis previa se mantiene o ha quedado invalidada;
- recibir una alerta futura sin permanecer mirando;
- explorar un jugador, equipo o competición sin perder el partido.

La experiencia no debe generar nuevas decisiones retrospectivas ni usar animación para simular una actualización inexistente.

## 3.4 Descanso

El usuario puede querer:

- entender la primera parte en menos de un minuto;
- distinguir marcador de dominio real;
- conocer cambios, tarjetas, lesiones o sustituciones;
- comprobar qué escenario previo se mantiene;
- saber qué observar al reiniciarse el juego.

El descanso necesita una síntesis, no una repetición de todos los eventos.

## 3.5 Después del partido

El usuario puede querer:

- confirmar resultado y estado final;
- identificar hechos decisivos;
- revisar estadísticas finales;
- entender qué hipótesis se confirmó o falló;
- ver liquidación transparente del pick;
- descubrir el siguiente partido relevante;
- conservar el expediente en histórico;
- ajustar seguimiento sin perseguir pérdidas.

El aprendizaje debe explicar límites y muestra. No debe convertir un resultado aislado en una regla general.

## 3.6 Partido aplazado, suspendido o con datos insuficientes

El usuario necesita:

- conocer el estado exacto confirmado;
- saber qué información falta;
- ver cuándo se revisó por última vez;
- entender qué acciones quedan congeladas;
- saber si recibirá una actualización;
- evitar cualquier lectura, pick o alerta basada en una fase dudosa.

La ausencia de certeza es un estado de producto, no un hueco visual.

---

# 4. El recorrido de veinte minutos

El recorrido no presupone que el usuario permanezca veinte minutos. Define cómo debe crecer el valor si decide quedarse.

| Momento | Necesidad | Respuesta de experiencia | Señal de éxito |
|---|---|---|---|
| 0-10 s | Confirmar identidad y estado | Equipos, competición, hora Madrid, estado, marcador y frescura inequívocos | El usuario sabe dónde está |
| 10-30 s | Saber qué importa | Último cambio o próxima evidencia relevante | Entiende por qué mirar ahora |
| 30-60 s | Formar una lectura básica | Síntesis de hechos, contexto y cobertura | Puede explicar el momento con sus palabras |
| 1-3 min | Resolver una pregunta | Acceso directo a cronología, alineación, estadísticas o contexto | No recorre información irrelevante |
| 3-7 min | Profundizar | Relaciones entre eventos, jugadores, forma, clasificación y contexto | Comprende causas posibles sin falsa certeza |
| 7-12 min | Seguir cambios | Nuevos hechos integrados sin perder posición ni lectura previa | Detecta qué cambió |
| 12-16 min | Evaluar criterio | SHARK, pick y bankroll solo si existe evidencia y permiso | Separa dato, interpretación y decisión |
| 16-20 min | Cerrar o continuar | Favorito, alerta, Telegram, siguiente hito o salida con contexto guardado | Puede marcharse sin perder continuidad |

## 4.1 Visitas de retorno

Cuando el usuario vuelve, la experiencia debería responder:

- qué cambió desde su última visita;
- cuánto tiempo pasó;
- qué estado sigue vigente;
- qué información quedó obsoleta;
- cuál es el siguiente hecho relevante.

No debe obligarlo a leer otra vez todo el partido.

---

# 5. Modelo de atención

Match Center debe separar cinco capas conceptuales.

## 5.1 Hecho

Información confirmada:

- identidad;
- competición;
- fecha;
- estado;
- marcador;
- minuto o fase;
- evento;
- alineación;
- estadística;
- resultado.

## 5.2 Contexto

Información que ayuda a interpretar:

- clasificación;
- forma;
- H2H comparable;
- estadio;
- árbitro;
- entrenador;
- ausencias;
- rol de jugadores;
- situación competitiva.

## 5.3 Cambio

La diferencia respecto a una lectura anterior:

- gol;
- tarjeta;
- sustitución;
- alineación confirmada;
- cambio de fase;
- dato que quedó stale;
- revisión de pick;
- invalidación de una hipótesis.

## 5.4 Criterio

Interpretación explicable:

- lectura SHARK;
- razones;
- contraargumentos;
- riesgos;
- invalidadores;
- calidad del dato;
- recomendación de esperar.

## 5.5 Acción

Decisión controlada del usuario:

- seguir partido;
- abrir entidad relacionada;
- configurar alerta;
- abrir Telegram;
- revisar pick;
- consultar exposición de Bankroll;
- volver al Calendario conservando contexto.

Ninguna capa puede presentarse como otra. Un criterio no se muestra como hecho y una acción no se disfraza de urgencia.

---

# 6. Contrato funcional de la experiencia

Este contrato define para qué sirve cada elemento. No prescribe componentes visuales.

## 6.1 Identidad y cabecera

Debe responder:

- qué partido es;
- a qué competición y fase pertenece;
- cuándo ocurre en hora Madrid;
- qué equipos participan;
- cuál es su estado;
- si el dato es actual y completo.

Debe permanecer reconocible durante todo el recorrido. Los escudos usan fallback honesto si no existe un activo autorizado.

Nunca debe:

- deformar un escudo;
- mostrar minuto o marcador no confirmados;
- confundir confianza del dato con probabilidad;
- repetir la misma cabecera dentro del contenido.

## 6.2 Estado

Estados funcionales mínimos:

- programado;
- alineaciones pendientes;
- alineaciones confirmadas;
- próximo a comenzar;
- en directo;
- descanso;
- interrumpido;
- suspendido;
- aplazado;
- finalizado;
- resultado pendiente de verificación;
- dato stale;
- cobertura insuficiente.

Cada estado debe tener:

- significado humano;
- evidencia mínima;
- frescura;
- acciones permitidas;
- acciones bloqueadas;
- siguiente revisión esperada.

## 6.3 Marcador y tiempo

Solo aparecen cuando son reales. Deben comunicar:

- resultado actual o final;
- minuto o fase, si existe evidencia;
- estado de actualización;
- si la lectura quedó congelada por datos stale.

Nunca se interpola un minuto ni se anima un marcador para aparentar actividad.

## 6.4 Cronología y eventos

La cronología responde:

- qué ocurrió;
- cuándo ocurrió;
- quién participó;
- cómo cambió el partido;
- qué evento es nuevo desde la última visita.

Eventos posibles solo si la fuente los certifica:

- goles;
- tarjetas;
- sustituciones;
- penaltis;
- VAR;
- lesiones comunicadas;
- inicio, descanso, reanudación y final;
- incidencias oficiales.

La cronología no debe llenarse con mensajes editoriales repetitivos.

## 6.5 Estadísticas

Cada estadística debe responder una pregunta. Debe incluir:

- nombre comprensible;
- valor por equipo;
- periodo;
- frescura;
- cobertura;
- relación con el momento cuando exista.

Las estadísticas no disponibles se omiten o se explican. No se muestran ceros como sustituto de ausencia.

## 6.6 Alineaciones

Debe diferenciar:

- prevista;
- pendiente;
- confirmada;
- actual en live;
- final registrada.

La alineación confirmada debe conectar jugadores con:

- posición o rol cuando la fuente lo permita;
- titularidad;
- eventos;
- sustitución;
- Player Center futuro.

Nunca se presenta una alineación probable como oficial.

## 6.7 Suplentes

Los suplentes forman parte del mismo estado de alineación. Deben permitir entender:

- quién está disponible;
- quién entró;
- a quién sustituyó;
- cuándo ocurrió;
- quién permaneció sin participar.

No se infieren motivos de una sustitución.

## 6.8 Entrenadores

Se muestran cuando están confirmados y aportan contexto. Su presencia debe conectar con:

- equipo;
- planteamiento confirmado, si existe fuente;
- cambios efectuados;
- historial pertinente sin atribuir intenciones no declaradas.

## 6.9 Árbitro

Debe incluirse cuando la fuente sea fiable y tenga valor contextual. Nunca se convierte su historial en una predicción determinista.

## 6.10 Estadio

Debe responder dónde se juega y, si existe evidencia, si cambió la sede. No se infiere asistencia, clima o ventaja sin fuente autorizada.

## 6.11 Forma

La forma debe declarar:

- muestra;
- periodo;
- local o visitante cuando corresponda;
- competición o mezcla;
- rivales comparables;
- limitaciones.

Una secuencia de resultados no equivale automáticamente a tendencia.

## 6.12 H2H

Los enfrentamientos directos deben demostrar comparabilidad:

- antigüedad;
- competición;
- contexto local/visitante;
- número de partidos;
- cambios estructurales relevantes cuando se conozcan.

Si la muestra no es útil, debe decirlo.

## 6.13 Clasificación

Debe situar:

- posición;
- puntos;
- partidos jugados;
- objetivo o fase cuando sea verificable;
- efecto provisional del resultado si puede calcularse con reglas certificadas.

No se muestra una tabla parcial engañosa ni una proyección como oficial.

## 6.14 Lesiones y ausencias

Solo aparecen con fuente y estado:

- confirmada;
- sanción;
- duda informada;
- regreso confirmado;
- información limitada.

Nunca se infiere una lesión por ausencia de alineación.

## 6.15 Favoritos

Seguir un partido debe producir una consecuencia clara:

- acceso prioritario;
- retorno contextual;
- opción de alerta;
- control para dejar de seguir.

Favorito no significa pick, recomendación ni importancia deportiva.

## 6.16 Competición

Debe conectar el partido con:

- jornada o fase;
- clasificación;
- otros resultados relevantes;
- Competition Center futuro;
- reglas competitivas verificadas.

El usuario puede explorar la competición y volver al mismo partido y contexto.

## 6.17 Equipo

Cada equipo debe conectar con:

- Team Center futuro;
- forma;
- calendario;
- clasificación;
- plantilla;
- jugadores;
- partidos relacionados.

La navegación no debe reemplazar el Match Center ni perder su estado.

## 6.18 Jugador

Cada jugador confirmado puede conectar con:

- Player Center futuro;
- rol;
- eventos del partido;
- disponibilidad;
- estadísticas relevantes.

No se abren perfiles vacíos cuando no existe cobertura suficiente.

## 6.19 SHARK

SHARK debe responder una pregunta concreta:

- qué evidencia importa;
- qué cambió;
- qué riesgo existe;
- qué invalidaría la lectura;
- qué falta;
- por qué conviene esperar.

Debe separar:

- dato;
- interpretación;
- incertidumbre;
- recomendación.

Nunca debe:

- repetir toda la ficha;
- garantizar beneficio;
- inventar contexto;
- crear urgencia;
- cambiar pesos o stake;
- ocultar una muestra insuficiente.

## 6.20 Picks

Un pick solo aparece si supera su pipeline real. Debe indicar:

- mercado;
- selección;
- cuota real y frescura;
- estado;
- revisión;
- razones;
- riesgos;
- invalidadores;
- resultado cuando corresponda.

El partido mantiene su valor aunque no exista pick.

## 6.21 Bankroll

Bankroll debe ayudar a responder:

- qué exposición voluntaria existe;
- qué límite personal se ha configurado;
- si existe concentración;
- qué ocurriría en escenarios orientativos.

Nunca:

- ejecuta apuestas;
- mueve dinero;
- aumenta stake;
- recomienda recuperar pérdidas;
- convierte una cuota en expectativa garantizada.

## 6.22 Telegram

Telegram debe permitir:

- elegir qué cambio merece una alerta;
- conocer si el seguimiento está activo;
- evitar mensajes duplicados;
- volver al punto exacto del partido;
- respetar membresía, horario Madrid y límites.

No debe existir un CTA Telegram repetido en cada módulo.

---

# 7. Comportamiento por ciclo de vida

| Fase | Prioridad principal | Contexto secundario | SHARK | Pick | Acción natural |
|---|---|---|---|---|---|
| Previa lejana | Identidad, hora y situación competitiva | Forma, clasificación, H2H comparable | Qué falta por confirmar | Solo si es publicable | Seguir o volver después |
| Previa cercana | Alineaciones, ausencias y cambios | Riesgos y contexto actualizado | Vigencia de la lectura | Revisado o bloqueado | Activar alerta útil |
| Inicio | Estado y confirmación | Alineación definitiva | Qué cambió antes del inicio | Estado previo, sin reescritura | Seguir partido |
| Live | Marcador, fase y último hecho | Cronología y estadísticas frescas | Cambio relevante e invalidadores | Seguimiento del existente | Configurar siguiente alerta |
| Descanso | Síntesis de la primera parte | Eventos y estadísticas explicativas | Escenario vigente o invalidado | Estado transparente | Saber qué observar |
| Final | Resultado y hechos decisivos | Estadísticas finales | Aprendizaje con límites | Liquidación | Guardar expediente o continuar |
| Aplazado/suspendido | Estado oficial | Qué se sabe y qué falta | Sin lectura activa | Congelado | Esperar actualización |
| Stale | Última lectura válida congelada | Edad y limitación del dato | Sin nueva inferencia | No se actualiza | Salir o esperar |
| Cobertura insuficiente | Información disponible | Ausencias explícitas | “No hay evidencia suficiente” | No publicable | Seguir hechos básicos |

---

# 8. Alternativa A: Dossier deportivo

## 8.1 Idea

El partido se entiende como un expediente completo organizado por temas estables. La experiencia prioriza consulta, precisión y auditabilidad.

## 8.2 Recorrido de veinte minutos

1. Confirmar identidad y estado.
2. Elegir la pregunta: previa, alineaciones, estadísticas, contexto o decisión.
3. Consultar el bloque temático.
4. Comparar evidencia.
5. Abrir entidades relacionadas.
6. Revisar SHARK o pick si corresponde.
7. Guardar o configurar seguimiento.

## 8.3 Tratamiento de los módulos

- Cabecera, estado y marcador actúan como ancla común.
- Alineaciones, suplentes y entrenadores forman un expediente de participantes.
- Cronología y eventos forman el expediente temporal.
- Estadísticas forman el expediente cuantitativo.
- Forma, H2H, clasificación, lesiones, árbitro y estadio forman el expediente contextual.
- SHARK, picks y Bankroll forman el expediente de criterio responsable.
- Telegram y favoritos forman el expediente de seguimiento.
- Equipos, competición y jugadores funcionan como relaciones navegables.

## 8.4 Ventajas

- Cobertura completa y fácil de auditar.
- El usuario sabe dónde buscar un tipo concreto de dato.
- Degrada bien cuando falta un módulo.
- Facilita distinguir FREE de profundidad premium sin ocultar hechos.
- Es estable entre previa, live y final.

## 8.5 Desventajas

- El usuario debe construir por sí mismo la historia.
- “Qué cambió” puede quedar repartido.
- Aumenta el coste de alternar entre eventos y contexto.
- Puede favorecer acumulación de módulos.
- Una visita rápida puede sentirse más pesada de lo necesario.

## 8.6 Complejidad

**Media.** La dificultad principal es gobernar el hogar único de cada dato y evitar expedientes redundantes.

## 8.7 Escalabilidad

**Alta en cobertura, media en atención.** Añadir datos es sencillo, pero cada nuevo bloque aumenta el coste cognitivo.

## 8.8 Valor

| Dimensión | Valor |
|---|---|
| Usuario | Alto para consulta profunda; medio para visitas rápidas |
| Empresa | Alto por auditabilidad y segmentación de valor |
| SHARK | Alto como capa de síntesis; riesgo de quedar aislado |
| Telegram | Alto para enlaces a un tema concreto |
| Móvil | Medio por longitud y saltos entre temas |
| Desktop | Muy alto para exploración comparada |

## 8.9 Riesgo principal

Convertir Match Center en un archivo deportivo correcto pero sin narrativa.

## 8.10 Hipótesis a validar

Los usuarios que llegan con una pregunta concreta encuentran el dato más rápido que en una experiencia adaptativa.

---

# 9. Alternativa B: Línea temporal total

## 9.1 Idea

El partido se vive como una secuencia continua desde la primera evidencia previa hasta el aprendizaje final. Todo cambio relevante entra en una historia cronológica verificable.

## 9.2 Recorrido de veinte minutos

1. Confirmar el estado actual.
2. Ver el último cambio.
3. Retroceder hasta el contexto necesario.
4. Seguir nuevos eventos.
5. Abrir detalles asociados a un hito.
6. Configurar el siguiente aviso.
7. Volver después al último punto leído.

## 9.3 Tratamiento de los módulos

- Estado, marcador y fase determinan el presente.
- Alineaciones, lesiones confirmadas, cambios de pick y mensajes Telegram aparecen como hitos.
- Goles, tarjetas, sustituciones y VAR forman la columna vertebral live.
- Estadísticas se anclan al periodo que ayudan a explicar.
- Forma, H2H y clasificación aparecen como contexto previo, no como eventos live repetidos.
- SHARK registra cambios de lectura contra evidencia anterior.
- El resultado, la liquidación y el aprendizaje cierran la historia.

## 9.4 Ventajas

- Excelente continuidad antes, durante y después.
- “Qué cambió” se vuelve inmediato.
- El retorno puede recuperar el último punto leído.
- Telegram encaja naturalmente como extensión de hitos.
- El aprendizaje posterior conserva trazabilidad.

## 9.5 Desventajas

- Una secuencia extensa puede generar ruido.
- Los datos estructurales quedan dispersos.
- Comparar estadísticas o alineaciones completas requiere una vista secundaria.
- Un proveedor verboso puede dominar la experiencia.
- Existe riesgo de confundir actividad con relevancia.

## 9.6 Complejidad

**Alta.** Requiere dedupe, orden temporal fiable, prioridad editorial y tratamiento riguroso de correcciones.

## 9.7 Escalabilidad

**Media.** Escala bien en duración, pero no en volumen de eventos sin filtrado y agrupación.

## 9.8 Valor

| Dimensión | Valor |
|---|---|
| Usuario | Muy alto para seguimiento y retorno; medio para consulta temática |
| Empresa | Alto por recurrencia y trazabilidad |
| SHARK | Muy alto para explicar cambios y revisar hipótesis |
| Telegram | Muy alto por correspondencia entre alerta e hito |
| Móvil | Muy alto por lectura secuencial |
| Desktop | Alto, con riesgo de infrautilizar comparación lateral |

## 9.9 Riesgo principal

Crear un feed de actividad que premie frecuencia en lugar de significado.

## 9.10 Hipótesis a validar

El usuario comprende mejor el partido cuando contexto y hechos aparecen en el orden en que cambiaron.

---

# 10. Alternativa C: Sala de decisión responsable

## 10.1 Idea

El partido se organiza alrededor de una pregunta: ¿existe una decisión responsable que merezca atención? La experiencia concentra evidencia, riesgos, invalidadores y exposición.

## 10.2 Recorrido de veinte minutos

1. Confirmar estado y calidad del dato.
2. Entender si existe decisión o conviene esperar.
3. Revisar evidencia a favor y en contra.
4. Consultar alineaciones, forma, eventos y estadísticas que sustentan la lectura.
5. Revisar pick y exposición, si existen.
6. Configurar una alerta sobre el invalidado o hito relevante.
7. Volver cuando cambie la evidencia.

## 10.3 Tratamiento de los módulos

- Cabecera y marcador conservan la identidad deportiva.
- SHARK ordena evidencia, contraargumentos y límites.
- El pick aparece solo como resultado de un pipeline válido.
- Bankroll muestra exposición voluntaria y límites.
- Alineaciones, eventos, estadísticas, forma, H2H, clasificación y lesiones son fuentes de evidencia.
- Telegram avisa únicamente cuando cambia una condición relevante.
- Equipos, jugadores y competición permiten verificar contexto.

## 10.4 Ventajas

- Diferenciación clara de NeMeSiS.
- Reduce estadísticas decorativas.
- Hace visibles riesgo e incertidumbre.
- El valor premium es comprensible.
- Puede concluir honestamente que no hay decisión.

## 10.5 Desventajas

- Puede reducir el deporte a una oportunidad de apuesta.
- Un usuario que solo quiere seguir el partido puede sentirse fuera de lugar.
- Depende de datos y gobierno de picks más exigentes.
- Puede sobrerrepresentar SHARK.
- Eleva el riesgo legal, ético y reputacional si el tono falla.

## 10.6 Complejidad

**Alta.** Exige contratos sólidos, explicación verificable, membresías coherentes y guardrails de juego responsable.

## 10.7 Escalabilidad

**Media.** Escala solo donde hay cobertura y evidencia suficiente para una lectura responsable.

## 10.8 Valor

| Dimensión | Valor |
|---|---|
| Usuario | Muy alto para criterio; bajo/medio para seguimiento deportivo puro |
| Empresa | Muy alto para propuesta premium; riesgo reputacional elevado |
| SHARK | Central y muy alto |
| Telegram | Muy alto para alertas de cambio, con límites estrictos |
| Móvil | Alto si la decisión es breve y explicable |
| Desktop | Muy alto para escenarios y evidencia |

## 10.9 Riesgo principal

Contradecir la promesa “NeMeSiS vende criterio, no apuestas” al convertir el pick en el centro del partido.

## 10.10 Hipótesis a validar

La claridad de “actuar, esperar o ignorar” aporta valor sin desplazar el interés deportivo.

---

# 11. Alternativa D: Historia viva por ciclo

## 11.1 Idea

Una identidad permanece estable y la experiencia cambia de prioridad según la fase y la evidencia. No cambia la historia; cambia lo que merece atención ahora.

## 11.2 Recorrido de veinte minutos

1. Confirmar partido y estado.
2. Ver el cambio o la próxima evidencia relevante.
3. Comprender la síntesis de la fase actual.
4. Profundizar en cronología, alineaciones, estadísticas o contexto.
5. Revisar SHARK y pick solo si son pertinentes.
6. Configurar continuidad.
7. Volver al mismo partido en otra fase sin reaprenderlo.

## 11.3 Tratamiento de los módulos

- Identidad, equipos y competición permanecen estables.
- La previa prioriza hora, contexto, alineaciones y ausencias.
- El inicio prioriza confirmaciones y cambios.
- Live prioriza marcador, fase, último hecho y cronología.
- El descanso prioriza síntesis e invalidadores.
- El final prioriza resultado, hechos decisivos, liquidación y aprendizaje.
- Estadísticas, H2H, forma y clasificación suben o bajan según la pregunta.
- SHARK responde a la fase actual.
- Telegram y favoritos preservan continuidad.
- Bankroll aparece solo cuando existe exposición configurada.

## 11.4 Ventajas

- Conserva una sola historia durante todo el ciclo.
- Reduce carga cognitiva sin ocultar profundidad.
- Admite visitas rápidas y largas.
- Funciona con cobertura variable mediante prioridades y estados seguros.
- Integra SHARK y Telegram sin convertirlos en destinos separados.

## 11.5 Desventajas

- Requiere reglas editoriales rigurosas.
- Un cambio de prioridad inesperado puede desorientar.
- Es más difícil probar que una estructura completamente estable.
- Depende de lifecycle y frescura correctos.
- Puede esconder profundidad si las rutas de acceso no son claras.

## 11.6 Complejidad

**Alta.** La dificultad no es la cantidad de módulos, sino decidir con evidencia qué merece atención en cada fase.

## 11.7 Escalabilidad

**Alta** si todos los módulos usan el mismo contrato y degradan sin inventar datos.

## 11.8 Valor

| Dimensión | Valor |
|---|---|
| Usuario | Muy alto por continuidad y reducción de esfuerzo |
| Empresa | Muy alto por retorno, confianza y profundidad comercial responsable |
| SHARK | Muy alto como criterio contextual |
| Telegram | Muy alto como continuidad entre fases |
| Móvil | Muy alto si la prioridad es secuencial y estable |
| Desktop | Muy alto si permite profundizar sin perder el presente |

## 11.9 Riesgo principal

Una transición incorrecta puede mostrar una prioridad o fase que no coincide con la realidad.

## 11.10 Hipótesis a validar

Una experiencia adaptada al ciclo reduce tiempo y esfuerzo sin hacer que el usuario pierda orientación.

---

# 12. Alternativa E: Lectura esencial y profundidad bajo demanda

## 12.1 Idea

La experiencia ofrece una lectura esencial universal y permite ampliar progresivamente hasta el expediente completo. No se obliga a todos a consumir la misma profundidad.

## 12.2 Recorrido de veinte minutos

1. Resolver estado, marcador y cambio en la lectura esencial.
2. Elegir una pregunta concreta.
3. Ampliar contexto, cronología, estadísticas, participantes o criterio.
4. Cerrar la profundidad sin perder el estado actual.
5. Guardar la preferencia de profundidad solo con control del usuario.
6. Configurar continuidad o salir.

## 12.3 Tratamiento de los módulos

- La lectura esencial contiene identidad, estado, marcador, frescura y último cambio.
- Cronología, estadísticas, alineaciones y contexto se revelan por intención.
- Entrenadores, árbitro, estadio, H2H, clasificación y lesiones aparecen cuando resuelven una pregunta.
- SHARK ofrece síntesis y acceso a evidencia.
- Picks y Bankroll permanecen en una profundidad responsable.
- Telegram y favoritos forman acciones de continuidad, no contenido.

## 12.4 Ventajas

- Reduce densidad inicial.
- Sirve a usuarios con distinto nivel de conocimiento.
- Mantiene hechos básicos accesibles.
- Facilita uso móvil.
- Puede educar progresivamente sin saturar.

## 12.5 Desventajas

- Puede ocultar información que el usuario no sabe que existe.
- La profundidad puede requerir demasiadas decisiones.
- Existe riesgo de mantener dos experiencias incoherentes.
- Recordar preferencias puede complicar el retorno.
- Un exceso de expansión y cierre añade fricción.

## 12.6 Complejidad

**Alta.** Exige gobernar progresión, descubribilidad, memoria de estado y equivalencia funcional.

## 12.7 Escalabilidad

**Media/alta.** Admite muchos módulos, pero cada nivel aumenta el coste de mantener coherencia.

## 12.8 Valor

| Dimensión | Valor |
|---|---|
| Usuario | Alto por control de profundidad; riesgo de descubrimiento |
| Empresa | Alto para educación y segmentación |
| SHARK | Alto al separar síntesis y evidencia |
| Telegram | Alto si enlaza a la profundidad exacta |
| Móvil | Muy alto |
| Desktop | Alto, aunque puede ocultar capacidad útil |

## 12.9 Riesgo principal

Convertir la profundidad bajo demanda en dos productos que muestran verdades o prioridades diferentes.

## 12.10 Hipótesis a validar

Los usuarios comprenden mejor la información cuando eligen la profundidad, sin perder datos relevantes ni orientación.

---

# 13. Comparación de alternativas

Esta matriz no elige ganadora. Resume compromisos para preparar prototipos y pruebas.

| Criterio | A Dossier | B Cronología | C Decisión | D Historia por ciclo | E Profundidad |
|---|---|---|---|---|---|
| Orientación inmediata | Alta | Alta | Alta | Muy alta | Muy alta |
| Continuidad temporal | Media | Muy alta | Alta | Muy alta | Alta |
| Consulta temática | Muy alta | Media | Alta | Alta | Alta |
| “Qué cambió” | Media | Muy alta | Alta | Muy alta | Alta |
| Seguimiento live | Alta | Muy alta | Alta | Muy alta | Alta |
| Visita rápida | Media | Alta | Muy alta | Muy alta | Muy alta |
| Exploración de 20 min | Muy alta | Alta | Alta | Muy alta | Alta |
| Datos incompletos | Alta | Media | Media | Muy alta | Alta |
| Riesgo de ruido | Alto | Muy alto | Medio | Medio | Medio |
| Riesgo de ocultación | Bajo | Medio | Alto | Medio | Alto |
| Riesgo de presión comercial | Bajo | Bajo | Muy alto | Bajo | Medio |
| Coherencia móvil | Media | Muy alta | Alta | Muy alta | Muy alta |
| Coherencia desktop | Muy alta | Alta | Muy alta | Muy alta | Alta |
| Valor SHARK | Alto | Muy alto | Muy alto | Muy alto | Alto |
| Valor Telegram | Alto | Muy alto | Muy alto | Muy alto | Alto |
| Complejidad operativa | Media | Alta | Alta | Alta | Alta |
| Escalabilidad de cobertura | Alta | Media | Media | Alta | Media/alta |
| Auditabilidad | Muy alta | Alta | Alta | Alta | Media/alta |

## 13.1 Tensiones que la decisión debe resolver

- estabilidad temática frente a prioridad adaptativa;
- cobertura completa frente a reducción de ruido;
- cronología frente a comparabilidad;
- criterio premium frente a seguimiento deportivo universal;
- simplicidad inicial frente a descubribilidad;
- personalización frente a previsibilidad;
- continuidad live frente a coste operativo;
- profundidad frente a velocidad;
- automatización editorial frente a control humano.

---

# 14. Lectura del Product Board

No son votos ni una decisión. Son preguntas que cada área exige resolver.

## CEO

- ¿La alternativa expresa una ventaja propia de NeMeSiS?
- ¿Puede explicarse en una frase sin promesas exageradas?
- ¿Aumenta confianza además de permanencia?

## Producto

- ¿Qué trabajo completo resuelve?
- ¿Qué información elimina, subordina o conserva?
- ¿Cómo funciona en visitas repetidas?

## UX

- ¿El usuario sabe dónde está, qué cambió y qué puede hacer?
- ¿Cuántas decisiones necesita para resolver una pregunta?
- ¿La experiencia funciona con conocimiento deportivo bajo y alto?

## Frontend

- ¿La prioridad puede cambiar sin saltos, duplicación ni pérdida de foco?
- ¿Móvil y desktop comparten la misma verdad?
- ¿La experiencia sigue siendo estable con contenido largo, vacío o tardío?

## Backend

- ¿Cada dato tiene un origen y lifecycle único?
- ¿Puede reconstruirse “qué cambió” con evidencia?
- ¿La ausencia, stale y corrección tienen semántica clara?

## Datos deportivos

- ¿Qué módulos tienen cobertura real?
- ¿Qué nivel de frescura exige cada estado?
- ¿Cómo se corrigen eventos sin borrar trazabilidad?

## SHARK

- ¿Responde preguntas concretas o decora?
- ¿Puede declarar insuficiencia?
- ¿Se distingue de probabilidad y calidad del dato?

## Telegram

- ¿Qué cambio justifica interrumpir al usuario?
- ¿El enlace devuelve al contexto exacto?
- ¿Cómo se evita duplicar lo que ya está visible?

## QA

- ¿Puede probarse cada fase, transición y estado degradado?
- ¿Qué invariantes deben mantenerse?
- ¿Qué datos faltantes podrían romper la comprensión?

## Sentinel

- ¿Puede detectar fase falsa, stale, duplicidad o prioridad incoherente?
- ¿Puede señalar el consumidor y la evidencia?
- ¿Evita falsos positivos cuando simplemente falta cobertura?

## AutoPilot

- ¿Puede crear una incidencia precisa sin modificar la experiencia?
- ¿Qué correcciones requieren aprobación humana?
- ¿Cómo evita convertir una hipótesis UX en un auto-fix?

## Company Intelligence

- ¿Qué señales agregadas demostrarían menos esfuerzo y más confianza?
- ¿Cómo separa correlación de causalidad?
- ¿Qué datos no debe recopilar?

## Operations

- ¿Qué necesita el administrador para explicar un estado incorrecto?
- ¿Existe modo degradado?
- ¿Puede recuperarse sin alterar la historia del usuario?

---

# 15. Móvil y desktop

## 15.1 Principios comunes

- misma identidad;
- mismo estado;
- misma cronología;
- misma frescura;
- mismas reglas de visibilidad;
- mismas limitaciones;
- misma relación entre hecho, criterio y acción;
- retorno al mismo contexto.

## 15.2 Experiencia móvil

Debe favorecer:

- lectura con una mano;
- prioridad secuencial;
- acciones poco numerosas y claras;
- contexto actual reconocible durante desplazamiento;
- cambios visibles sin reiniciar posición;
- acceso rápido a cronología, participantes y seguimiento;
- retorno desde equipo, jugador o competición;
- safe area y teclado sin cubrir acciones.

No debe ser una versión comprimida de un escritorio exhaustivo.

## 15.3 Experiencia desktop

Debe favorecer:

- estado y contexto simultáneos;
- comparación sin duplicación;
- profundidad sin perder el presente;
- navegación entre entidades conservando el partido;
- lectura prolongada sin zonas vacías ni módulos decorativos.

No debe llenar espacio disponible solo porque existe.

---

# 16. Continuidad entre experiencias

## 16.1 Desde Calendario

Al abrir un partido deben conservarse:

- fecha;
- carril;
- filtros;
- posición;
- contexto de retorno.

Al volver, Calendario recupera exactamente la exploración anterior.

## 16.2 Hacia Team Center

El usuario explora un equipo para responder una pregunta del partido. Al regresar:

- el partido sigue en la misma fase;
- se conserva el punto de lectura;
- se destacan cambios ocurridos durante la ausencia.

## 16.3 Hacia Player Center

Solo se abre si existe una entidad y cobertura suficientes. El vínculo debe explicar por qué el jugador es relevante para este partido.

## 16.4 Hacia Competition Center

La competición aporta clasificación, jornada y contexto. No reemplaza el estado del partido.

## 16.5 Con Telegram

Cada alerta debe identificar:

- partido;
- cambio;
- momento;
- audiencia;
- dedupe;
- destino contextual.

El usuario vuelve al Match Center en el estado que motivó el mensaje, con una indicación clara de lo que cambió.

## 16.6 Con SHARK

SHARK puede abrir evidencia relacionada, pero la verdad deportiva permanece en su módulo canónico. No se clonan estadísticas ni eventos dentro de una narrativa separada.

---

# 17. Membresías y valor

## FREE

Debe comprender:

- identidad;
- estado;
- marcador real;
- cronología básica;
- alineaciones confirmadas disponibles;
- estadísticas esenciales disponibles;
- competición;
- frescura y limitaciones;
- seguimiento básico.

FREE no recibe una experiencia deliberadamente rota.

## PRO

Puede ampliar:

- lectura SHARK;
- razones y contraargumentos;
- pick publicable;
- riesgos e invalidadores;
- contexto comparado;
- alertas avanzadas;
- expediente y seguimiento.

## ELITE y ELITE+

Pueden ampliar, solo con evidencia:

- escenarios;
- análisis más profundo;
- seguimiento de cambios;
- exposición Bankroll voluntaria;
- aprendizaje histórico;
- continuidad premium entre web y Telegram.

Ningún plan recibe garantías, urgencia artificial o datos inventados.

---

# 18. Accesibilidad y serenidad

La alternativa elegida deberá garantizar:

- orden de lectura comprensible;
- foco visible;
- navegación completa por teclado;
- estados no dependientes solo del color;
- lenguaje claro para tiempo, fase y frescura;
- texto alternativo para activos relevantes;
- tablas con alternativa legible;
- controles táctiles suficientes;
- reducción de movimiento;
- actualizaciones live anunciadas sin interrumpir constantemente;
- marcador y cronología comprensibles por tecnologías de asistencia.

Live debe sentirse actual, no ansioso.

---

# 19. Juego responsable y ética

Match Center nunca debe:

- garantizar beneficio;
- presentar el partido como una obligación de actuar;
- usar cuenta atrás para presionar una apuesta;
- recomendar recuperar pérdidas;
- aumentar stake automáticamente;
- confundir marcador con oportunidad;
- publicar picks retrospectivos;
- ocultar riesgo o invalidadores;
- usar notificaciones para fomentar comportamiento compulsivo;
- experimentar con precio, riesgo, stake o información legal.

La acción de mayor confianza puede ser:

> “No existe evidencia suficiente. Sigue el partido sin tomar una decisión”.

---

# 20. Estados seguros

## Sin alineaciones

Explicar que están pendientes, cuándo se espera revisión y qué análisis permanece condicionado.

## Sin eventos detallados

Mostrar marcador y estado confirmados sin inventar cronología.

## Sin estadísticas

No sustituir ausencia por cero. Mantener hechos disponibles y explicar cobertura.

## Sin lesiones

No mostrar “sin lesiones” salvo que la fuente certifique una lista completa.

## Sin H2H comparable

Explicar que la muestra no aporta contexto suficiente.

## Sin pick

El partido conserva toda su utilidad deportiva. No se muestra un hueco comercial.

## Sin lectura SHARK

Indicar si falta evidencia, revisión o acceso. No generar texto genérico.

## Fuente stale

Congelar la última lectura válida, mostrar edad y bloquear nuevas inferencias.

## Corrección de proveedor

Mantener trazabilidad de la corrección y actualizar cualquier consecuencia dependiente.

---

# 21. Calidad futura: Sentinel, AutoPilot y Company Intelligence

Esta sección define aprendizaje de producto, no autoriza motores ni código.

## 21.1 Sentinel debería detectar

- marcador o minuto sin evidencia;
- fase incoherente con lifecycle;
- live stale presentado como actual;
- evento duplicado o desordenado;
- alineación probable etiquetada como confirmada;
- cero usado como sustituto de dato ausente;
- dato repetido en varios hogares;
- pick incompleto o retrospectivo;
- SHARK presentado como hecho;
- confianza del dato presentada como probabilidad;
- CTA Telegram duplicado;
- pérdida de contexto al volver;
- mezcla de navegación cliente/admin;
- overflow, texto cortado y acciones inaccesibles;
- cambio de prioridad que oculta un hecho crítico;
- módulo vacío sin explicación.

## 21.2 AutoPilot debería generar

- incidencia concreta;
- fase y ruta afectadas;
- evidencia;
- contrato incumplido;
- consumidores probables;
- impacto cliente;
- pruebas requeridas;
- propuesta de investigación;
- aprobación humana obligatoria para código, datos, rutas o experiencia.

AutoPilot no debe cambiar la alternativa de diseño, la prioridad editorial ni el producto.

## 21.3 Company Intelligence debería medir

Solo de forma agregada y respetuosa:

- tiempo hasta entender estado;
- tiempo hasta localizar un módulo;
- retorno al mismo partido;
- uso por fase;
- búsquedas o aperturas sin resultado;
- módulos ignorados;
- alertas configuradas y desactivadas;
- errores, stale y datos incompletos;
- uso de SHARK con resultado de tarea;
- salida hacia otra entidad y retorno;
- soporte relacionado con partidos;
- conversión atribuible solo cuando exista evidencia.

No debe:

- interpretar permanencia como satisfacción;
- usar tracking invasivo;
- optimizar presión de apuesta;
- declarar causalidad sin experimento válido;
- convertir una hipótesis en verdad.

---

# 22. Investigación necesaria antes de decidir

## 22.1 Participantes

Como mínimo:

- usuario que solo sigue resultados;
- usuario que analiza partidos;
- usuario FREE;
- usuario PRO/ELITE;
- usuario principalmente móvil;
- usuario principalmente desktop;
- usuario que utiliza Telegram;
- usuario con necesidades de accesibilidad.

## 22.2 Tareas

1. Confirmar si un partido está live y actualizado.
2. Encontrar el último evento relevante.
3. Saber si las alineaciones están confirmadas.
4. Explicar qué cambió desde la última visita.
5. Identificar qué estadística explica el momento.
6. Comprobar un jugador sustituido.
7. Entender clasificación y contexto competitivo.
8. Saber si existe pick y qué podría invalidarlo.
9. Configurar una única alerta útil.
10. Volver al Calendario sin perder contexto.
11. Comprender un estado stale.
12. Explicar por qué SHARK recomienda esperar.

## 22.3 Escenarios

- previa con datos completos;
- previa sin alineaciones;
- live con eventos y estadísticas;
- live con marcador pero cobertura parcial;
- descanso;
- final con pick;
- final sin pick;
- partido aplazado;
- proveedor stale;
- corrección de evento;
- visita de retorno después de cinco minutos.

## 22.4 Métricas

- éxito de tarea;
- tiempo de orientación;
- tiempo hasta el dato;
- errores de interpretación;
- retornos innecesarios;
- cambios de contexto;
- confianza declarada;
- comprensión de frescura;
- comprensión de SHARK;
- recuerdo de la siguiente acción;
- carga percibida;
- preferencia razonada.

No se usará únicamente tiempo en página.

---

# 23. Prototipos conceptuales requeridos

Antes de implementar, cada alternativa debe representarse con el mismo partido y los mismos datos en:

- previa;
- live;
- descanso;
- final;
- stale;
- cobertura insuficiente;
- desktop;
- móvil.

Las cinco alternativas deben utilizar:

- idéntico contenido;
- idéntica frescura;
- idénticos permisos;
- idénticas limitaciones;
- idéntica tarea;
- idéntico tiempo de prueba.

No es válido hacer una alternativa visualmente más completa para favorecerla.

---

# 24. Criterios de decisión

La alternativa elegida deberá demostrar:

1. Orientación inmediata.
2. Comprensión de “qué cambió”.
3. Continuidad antes, durante y después.
4. Reducción de esfuerzo.
5. Profundidad sin saturación.
6. Modo seguro con datos incompletos.
7. Integración responsable de SHARK.
8. Integración no invasiva de Telegram.
9. Utilidad deportiva sin pick.
10. Coherencia móvil y desktop.
11. Accesibilidad.
12. Auditabilidad.
13. Operación y recuperación.
14. Escalabilidad de cobertura.
15. Valor comercial sin promesa falsa.

## 24.1 Vetos

Una alternativa queda descartada si:

- necesita inventar datos;
- oculta frescura;
- presenta una opinión como hecho;
- reduce el partido a una apuesta;
- crea presión irresponsable;
- pierde contexto al cambiar de entidad;
- exige dos verdades distintas en móvil y desktop;
- no puede funcionar en modo degradado;
- impide auditar una corrección;
- depende de personalización opaca;
- requiere que el usuario reaprenda la experiencia en cada fase.

---

# 25. Preguntas abiertas

1. ¿Cuál es el mínimo contexto que debe permanecer reconocible durante toda la visita?
2. ¿Qué cambio merece ocupar la primera atención?
3. ¿Cómo se evita que la cronología se convierta en un feed?
4. ¿Cuándo una estadística explica y cuándo solo decora?
5. ¿Qué cobertura real existe para alineaciones, suplentes, árbitro, estadio y lesiones?
6. ¿Cómo se representa una corrección de proveedor sin confundir?
7. ¿Qué profundidad debe ser siempre FREE?
8. ¿Qué valor premium ahorra esfuerzo de forma demostrable?
9. ¿Cómo cambia la prioridad sin mover el suelo bajo el usuario?
10. ¿Qué preferencias deben recordarse y durante cuánto tiempo?
11. ¿Qué alertas justifican una interrupción?
12. ¿Cómo se mide que el usuario ya no necesita otra aplicación sin tracking invasivo?
13. ¿Qué versión funciona mejor para quien solo quiere el marcador?
14. ¿Qué versión funciona mejor para quien analiza veinte minutos?
15. ¿Qué coste operativo tiene cada alternativa por partido y proveedor?

---

# 26. Decisión pendiente

Este documento **no elige** entre A, B, C, D o E.

La visión superior ya aprobada exige una sola historia del partido y continuidad durante su ciclo. Las cinco alternativas estudian cómo cumplirla, con compromisos diferentes.

La decisión solo podrá tomarse después de:

1. confirmar cobertura real;
2. crear prototipos conceptuales equivalentes;
3. probar tareas con usuarios representativos;
4. revisar accesibilidad y juego responsable;
5. evaluar operación y recuperación;
6. comparar evidencia, no preferencias internas;
7. documentar la alternativa elegida y las partes subordinadas de las demás.

Hasta entonces:

`MATCH_CENTER_DIRECTION = UNDER_EVALUATION`

`IMPLEMENTATION_AUTHORIZED = FALSE`

`PRODUCTION_MODIFIED = FALSE`

La siguiente acción correcta no es programar. Es someter las cinco alternativas a la misma prueba de experiencia y decidir con evidencia cuál ayuda mejor al usuario durante sus siguientes veinte minutos.
