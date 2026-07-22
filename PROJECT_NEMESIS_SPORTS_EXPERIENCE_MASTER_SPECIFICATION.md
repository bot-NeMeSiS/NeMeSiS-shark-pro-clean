# PROJECT NEMESIS SPORTS EXPERIENCE MASTER SPECIFICATION

## 0. Propósito

Este documento define la futura experiencia deportiva de NeMeSiS SHARK PRO. Es una especificación funcional, no un plan técnico y no autoriza implementación.

La meta no es reunir más datos que otras aplicaciones. La meta es que el usuario pueda entender qué ocurre, qué merece atención y qué decisión es responsable sin abandonar NeMeSiS.

### Promesa de producto

NeMeSiS convierte información deportiva dispersa en un recorrido de decisión:

1. Qué ocurre.
2. Qué cambió.
3. Qué merece atención.
4. Qué evidencia existe.
5. Qué riesgo falta por resolver.
6. Qué puede hacer el usuario ahora.

### Principios obligatorios

- Una cifra debe tener fuente, frescura y contexto.
- Un dato incompleto se identifica como incompleto; nunca se rellena.
- SHARK aporta criterio, no certeza ni presión para apostar.
- Picks, Telegram y Bankroll aparecen solo cuando añaden valor al contexto deportivo.
- La personalización ayuda a priorizar, no encierra al usuario en una burbuja.
- Cada pantalla tiene una acción principal y evita duplicar módulos.
- FREE debe ser útil; PRO y ELITE deben ampliar profundidad, no ocultar hechos básicos.
- La ausencia de datos debe producir un estado seguro y útil.

## Referentes conceptuales, sin copia

| Concepto observado en el mercado | Qué funciona | Qué suele fallar | Respuesta NeMeSiS |
|---|---|---|---|
| Cobertura amplia | Reduce la necesidad de buscar otra fuente | Genera ruido y listas interminables | Cobertura organizada por relevancia personal y calidad del dato |
| Marcadores rápidos | Mantienen al usuario informado | El número aparece sin explicar el cambio | Marcador, contexto y hechos que explican el momento |
| Estadísticas extensas | Permiten profundizar | Mezclan señal y dato decorativo | Estadística priorizada por utilidad y explicada por SHARK |
| Alertas | Recuperan al usuario en el momento correcto | Exceso, duplicados y poca personalización | Alertas opt-in, deduplicadas y con motivo visible |
| Predicciones | Dan una respuesta inmediata | Pueden ocultar incertidumbre y fomentar falsa seguridad | Evidencia, escenarios, riesgos y recomendación de esperar cuando corresponda |

# 1. Calendario

## Objetivo

Contar la historia deportiva del día y permitir pasar de una visión general al partido relevante con el mínimo esfuerzo.

## Estructura funcional

- Cabecera temporal: Ayer, Hoy, Mañana y selector de fecha.
- Resumen del día: en directo, próximos, finalizados, con pick y favoritos.
- Bloques ordenados por estado y hora, agrupados por competición.
- Partido prioritario cuando exista evidencia suficiente; nunca por promoción artificial.
- Continuidad hacia la semana sin perder la fecha seleccionada.

## Filtros

- Estado: todos, próximos, en directo, descanso, finalizados y aplazados.
- Relación: favoritos, con pick, con análisis SHARK y con alerta activa.
- Geografía: país y región.
- Competición.
- Equipo.
- Franja horaria Madrid.
- Calidad del dato: confirmado, actualización pendiente o información limitada.

Los filtros deben ser acumulables, visibles y fáciles de restablecer. El usuario siempre debe saber por qué un partido aparece o no aparece.

## Navegación

- Cambio de fecha sin volver al inicio.
- Apertura directa de Match Center.
- Acceso a Team Center, Player Center y Competition Center desde entidades reconocibles.
- Estado y filtros conservados al volver atrás.

## Velocidad percibida

- La agenda visible debe aparecer de inmediato con la última información confirmada.
- Cambiar fecha o filtro no debe bloquear toda la pantalla.
- La actualización se comunica sin desplazar cards ni reiniciar el scroll.
- Un proveedor lento nunca bloquea el calendario.

## Diferencia SHARK

SHARK no añade otra predicción a cada partido. Clasifica la atención necesaria:

- Relevante ahora.
- Conviene esperar alineaciones.
- Datos insuficientes.
- Partido sin valor analítico.
- Revisión recomendada antes del inicio.

# 2. Match Center

## Objetivo

Ser la pantalla definitiva de un partido antes, durante y después, adaptando su prioridad al ciclo de vida real.

## Cabecera única

- Equipos y escudos o fallback honesto.
- Competición y jornada.
- Fecha y hora Madrid.
- Estado, marcador y minuto solo cuando estén confirmados.
- Favorito, compartir y alertas.
- Índice de Confianza del dato, claramente separado de una probabilidad deportiva.

## Módulos previos al partido

1. Estado y próxima actualización relevante.
2. Alineaciones confirmadas o estado pendiente.
3. Forma reciente y posición competitiva.
4. Ausencias confirmadas.
5. Enfrentamientos comparables, con tamaño de muestra visible.
6. Estadísticas que expliquen el contexto.
7. Pick, solo si supera el pipeline real.
8. Lectura SHARK: razones, riesgos, invalidadores y recomendación de esperar.
9. Acción Telegram relacionada con ese partido.
10. Impacto orientativo en Bankroll, solo para usuarios que lo hayan configurado.

## Módulos durante el partido

1. Marcador y tiempo confirmado.
2. Línea temporal de hechos reales.
3. Estadísticas live útiles y frescura.
4. Cambios respecto al escenario previo.
5. Alertas SHARK explicables, sin crear apuestas impulsivas.
6. Pick existente y su estado; nunca crear una selección retrospectiva.

## Módulos después del partido

1. Resultado verificable.
2. Hechos decisivos.
3. Estadísticas finales.
4. Liquidación transparente del pick.
5. Aprendizaje: qué hipótesis se confirmó, cuál falló y qué faltó.
6. Siguiente partido relevante de ambos equipos.

## Regla de no repetición

Cada dato tiene un único hogar. El marcador no se repite en varias cards; la cuota no aparece fuera del módulo de pick; SHARK referencia estadísticas existentes en lugar de clonarlas.

# 3. Team Center

## Objetivo

Responder quién es el equipo, qué le ocurre ahora y qué debería seguir el usuario.

## Contenido

- Identidad, competición principal y estado de seguimiento.
- Próximo partido y último resultado.
- Calendario reciente y próximo.
- Forma con muestra y rivalidad contextual.
- Clasificación y evolución.
- Plantilla actual confirmada.
- Lesiones, sanciones y dudas solo con fuente.
- Rendimiento local/visitante.
- Tendencias explicadas sin presentarlas como garantía.
- Picks vinculados e histórico evaluable.
- Noticias o cambios únicamente si existe fuente autorizada.

## Acciones

- Seguir equipo.
- Configurar alertas.
- Abrir próximo Match Center.
- Consultar lectura SHARK.
- Ver competiciones y jugadores relacionados.

# 4. Player Center

## Objetivo

Mostrar el impacto real del jugador sin convertir la pantalla en un archivo estadístico indiscriminado.

## Contenido

- Identidad, equipo, posición y disponibilidad.
- Próximo partido.
- Minutos y titularidades confirmadas.
- Forma reciente por métricas relevantes para su posición.
- Participación ofensiva, defensiva o creativa según rol.
- Lesiones, sanciones y retorno estimado solo si existe evidencia.
- Historial por competición y temporada.
- Comparación contextual con jugadores de rol equivalente.
- Hechos y cambios recientes.

## Límites

- No usar una puntuación sintética sin metodología visible.
- No comparar posiciones incompatibles.
- No inferir lesión, titularidad o estado emocional.
- SHARK distingue dato, interpretación e incertidumbre.

# 5. Competition Center

## Objetivo

Ofrecer una visión completa de una competición y una entrada rápida a lo importante de cada jornada.

## Contenido

- Identidad, temporada y fase.
- Jornada actual y próximas fechas.
- Clasificación con desempates explicados.
- Resultados y calendario.
- Equipos participantes.
- Líderes estadísticos cuando la fuente sea completa.
- Tendencias de la competición con muestra.
- Partidos con seguimiento, pick o alerta.
- Cobertura y frescura de datos.

## Experiencia

La competición conserva filtros y permite moverse entre clasificación, jornada, equipos y estadísticas sin perder contexto.

# 6. Live Center

## Objetivo

Transmitir que el deporte está ocurriendo sin sacrificar veracidad ni serenidad.

## Organización

- En directo ahora.
- Descanso.
- Próximos a comenzar.
- Finalizados recientemente.
- Favoritos primero cuando el usuario lo haya elegido.

## Card live

- Marcador, minuto o fase reales.
- Último hecho relevante.
- Estado de frescura.
- Indicador de cambio desde la última lectura.
- Pick vinculado y estado, si existe.
- Acceso inmediato al Match Center.

## Alertas y contexto

- Inicio, descanso, final y cambios decisivos configurables.
- Sin minuto ficticio ni animación que sugiera una actualización inexistente.
- Si el dato queda stale, se congela la última lectura, se etiqueta y se detiene cualquier inferencia.
- SHARK explica cambios relevantes solo cuando la evidencia supera el umbral definido.

# 7. Favoritos

## Objetivo

Crear una agenda personal útil, no una lista de estrellas sin consecuencias.

## Entidades

- Partidos.
- Equipos.
- Jugadores.
- Competiciones.
- Picks guardados.

## Funciones

- Resumen diario personalizado.
- Alertas por entidad y tipo de evento.
- Orden por actualidad y próxima acción.
- Historial de elementos seguidos.
- Control sencillo de frecuencia y canales.
- Explicación de por qué aparece cada recomendación.

# 8. Buscador global

## Objetivo

Llegar a cualquier entidad o acción relevante desde una única entrada.

## Resultados

- Partidos por equipo, fecha o competición.
- Equipos.
- Jugadores.
- Competiciones.
- Picks e histórico propio cuando el usuario tenga acceso.
- Acciones: ver hoy, abrir directos, revisar favoritos.

## Comportamiento

- Resultados agrupados por tipo.
- Coincidencia exacta primero y relevancia contextual después.
- Historial local controlable.
- Sin resultados patrocinados disfrazados.
- Estado claro cuando una entidad existe pero la cobertura es limitada.

# 9. Navegación

## Desktop

- Navegación principal persistente: Inicio, Partidos, Live, Picks y SHARK.
- Acceso secundario a Histórico, Telegram, Favoritos y Cuenta.
- Buscador global siempre disponible sin dominar la pantalla.
- Breadcrumbs solo en centros de entidad y profundidad real.

## Tablet

- Navegación compacta con prioridad a contexto y búsqueda.
- Paneles secundarios pasan a drawers o secciones consecutivas.
- Tablas se transforman en vistas comparables, no en scroll horizontal interminable.

## Mobile

- Bottom nav estable con cinco destinos esenciales.
- Header compacto con búsqueda, alertas y cuenta.
- Filtros en una superficie temporal con resumen de selecciones activas.
- Acción principal accesible con una mano.
- Safe area, teclado, scroll y retorno preservados.

## Regla transversal

Cliente y admin nunca comparten navegación. El destino actual siempre es reconocible y volver atrás recupera el contexto anterior.

# 10. Integración SHARK

## Cómo aparece

- Resumen de atención en Calendario.
- Contexto profundo en Match Center.
- Tendencias explicadas en Team, Player y Competition Center.
- Cambios relevantes en Live.
- Director deportivo completo en su espacio propio.

## Cuándo aparece

- Cuando existe una pregunta concreta que los datos pueden sostener.
- Cuando cambia una evidencia relevante.
- Cuando falta información y esperar es la mejor decisión.
- Cuando el usuario solicita una explicación.

## Qué explica

- Evidencia utilizada.
- Frescura y limitaciones.
- Razones a favor.
- Contraargumentos.
- Condiciones que invalidan la lectura.
- Diferencia entre calidad del dato y probabilidad deportiva.

## Qué nunca debe hacer

- Garantizar beneficio.
- Inventar alineaciones, minutos, cuotas o lesiones.
- Ocultar una muestra insuficiente.
- Empujar a apostar por urgencia.
- Cambiar stake o pesos automáticamente.
- Presentar una opinión como dato oficial.

# 11. Integración Telegram

## Relación con cada partido

- El Match Center muestra si existe alerta, pick o seguimiento Telegram para ese partido.
- El usuario elige eventos: inicio, alineación, cambio de cuota, pick publicado, resultado y cierre.
- Cada mensaje enlaza al contexto exacto dentro de NeMeSiS.
- El estado de entrega es visible sin exponer identificadores privados.

## Reglas

- Opt-in explícito.
- Dedupe por partido, evento y audiencia.
- Límites diarios y horario Madrid.
- FREE recibe utilidad real sin revelar análisis premium completo.
- PRO y ELITE reciben profundidad acorde a su plan y a la evidencia disponible.
- Nunca se envía contenido para rellenar una cuota de mensajes.

# 12. Integración Bankroll

## Objetivo

Ayudar a controlar exposición y disciplina, no a maximizar volumen de apuestas.

## Funciones

- Bankroll configurado voluntariamente.
- Unidades y límites personales.
- Exposición abierta por partido, competición y día.
- Historial de movimientos vinculados a picks reales.
- Alertas de concentración, racha y límite alcanzado.
- Escenarios orientativos antes de confirmar una decisión.

## Límites

- No mover dinero.
- No ejecutar apuestas.
- No recomendar recuperar pérdidas.
- No aumentar stake automáticamente.
- No mezclar rentabilidad estimada con resultados reales.
- Modo pausa y recursos de juego responsable siempre accesibles.

# 13. Integración Company Intelligence

## Objetivo

Medir si Sports Experience ayuda al usuario y conserva calidad, sin convertir la experiencia cliente en un panel operativo.

## Señales permitidas

- Cobertura y frescura por competición.
- Búsquedas sin resultado.
- Entidades favoritas y rutas utilizadas de forma agregada.
- Tiempo hasta encontrar un partido.
- Alertas configuradas, bloqueadas o duplicadas.
- Uso de SHARK y retorno al Match Center.
- Errores, estados stale y fallos de navegación.
- Conversión atribuible únicamente cuando exista evidencia.

## Decisiones que prepara

- Qué cobertura priorizar.
- Qué módulo genera ruido.
- Qué estado vacío necesita mejora.
- Dónde falta una fuente o contrato de datos.
- Qué regresión debe bloquear una release.

## Privacidad y gobierno

- Datos mínimos y agregados.
- Sin contenido sensible ni fingerprinting invasivo.
- Retención definida.
- Hipótesis separadas de resultados.
- Ningún cambio de producto, precio, pick o comunicación se autoaprueba.

# 14. Roadmap Sports Experience

## Orden exacto de implementación futura

### Etapa 0. Certificación de base

1. Cerrar el Backlog Oficial V939.
2. Certificar el Sports Data Contract y ciclos de vida.
3. Confirmar cobertura, costes, derechos de uso y límites de proveedores.
4. Definir analítica, privacidad y criterios de éxito.

### Etapa 1. Núcleo deportivo

5. Calendario unificado.
6. Match Center por estados: previo, live y final.
7. Favoritos de partidos y equipos.
8. Buscador global básico.
9. Navegación responsive del núcleo.

### Etapa 2. Contexto de entidades

10. Team Center.
11. Competition Center.
12. Player Center, únicamente con cobertura suficiente.
13. Búsqueda global completa entre entidades.

### Etapa 3. Tiempo real

14. Live Center sobre evidencia certificada.
15. Alertas configurables y deduplicadas.
16. Integración Telegram contextual.
17. QA de stale, backoff, coste y ventanas horarias.

### Etapa 4. Inteligencia responsable

18. SHARK contextual en Calendario y Match Center.
19. Explicaciones de cambios live.
20. Integración de picks con invalidadores y revisión.
21. Bankroll voluntario y guardrails responsables.

### Etapa 5. Operación y aprendizaje

22. Company Intelligence agregado.
23. Métricas de búsqueda, cobertura, retención y confianza.
24. Sentinel visual, contractual y de frescura.
25. Beta privada con observación humana.
26. Escalado progresivo por competición y proveedor.

## Gates entre etapas

Ninguna etapa avanza sin:

- Datos reales y derechos confirmados.
- Estado seguro para ausencia o retraso.
- Cero P0/P1 abiertos.
- Browser QA desktop, tablet y móvil.
- Accesibilidad y rendimiento aceptados.
- Coste operativo medido.
- Privacidad y juego responsable revisados.
- Rollback disponible.

## Decisión actual

`SPECIFICATION_ONLY`. No autoriza código, rutas, diseños visuales, proveedores, gasto de API, cambios de membresía ni despliegue.
