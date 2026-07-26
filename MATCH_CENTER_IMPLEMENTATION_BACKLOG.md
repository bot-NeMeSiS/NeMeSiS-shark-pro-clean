# Match Center Implementation Backlog

## 0. Control del documento

**Sprint estratégico:** `V943_MATCH_CENTER_DECISION_BOARD_FINAL`  
**Arquitectura aprobada:** Historia viva por ciclo  
**Contrato:** `MATCH-CENTER-LIFECYCLE-STORY-V1`  
**Estado:** `IMPLEMENTATION_READY / IMPLEMENTATION_NOT_STARTED`  
**Código autorizado por este documento:** no  
**Producción modificada:** no  

Este backlog traduce la decisión de producto en incrementos pequeños. No implementa ninguno.

---

# 1. Principios de ejecución

Cada Sprint debe:

1. resolver una capacidad completa;
2. preservar la ruta actual de detalle;
3. reutilizar componentes existentes cuando cumplan el contrato;
4. usar datos reales o estados seguros;
5. funcionar en FREE;
6. no depender de un Sprint futuro para no romperse;
7. incluir fallback;
8. incluir Browser QA;
9. incluir Sentinel;
10. incluir rollback;
11. poder desplegarse por sí mismo;
12. no introducir verdad duplicada.

## 1.1 Regla de despliegue independiente

Un Sprint es desplegable cuando:

- su estado incompleto se oculta o explica;
- el resto de Match Center sigue operativo;
- sus dependencias están presentes;
- no deja controles sin destino;
- no expone datos técnicos;
- no requiere datos inventados;
- puede revertirse sin perder DB o usuarios.

## 1.2 Gate previo a implementación

Antes del Sprint 1 debe existir una especificación técnica aprobada que confirme:

- ruta canónica existente;
- fuentes y tablas;
- contrato de match;
- lifecycle;
- componentes reutilizables;
- baseline de rendimiento;
- baseline Browser QA;
- estrategia de rollout;
- estado de DB y compatibilidad legacy;
- ausencia de nuevas rutas innecesarias.

Este gate no es un Sprint de producto.

---

# 2. Dependencias

```text
SPRINT 1 IDENTIDAD
→ SPRINT 2 ESTADO
→ SPRINT 3 CAMBIO Y SAFE MODE
→ SPRINT 4 TIMELINE
→ SPRINT 5 ESTADÍSTICAS
→ SPRINT 6 PARTICIPANTES
→ SPRINT 7 CONTEXTO
→ SPRINT 8 ENTIDADES
→ SPRINT 9 SHARK
→ SPRINT 10 PICKS
→ SPRINT 11 BANKROLL
→ SPRINT 12 CONTINUIDAD
→ SPRINT 13 EXPERIENCIA TRANSVERSAL
→ SPRINT 14 RELEASE GATE
```

Los Sprints 4, 5 y 6 pueden prepararse en paralelo después del Sprint 3, pero se integran de uno en uno.

---

# 3. Sprint 1: Identidad estable y retorno

## Objetivo

Crear el ancla permanente del partido sin cambiar su verdad deportiva.

## Resultado de usuario

El usuario reconoce inmediatamente:

- partido;
- equipos;
- competición;
- jornada o fase;
- fecha y hora Madrid;
- contexto de origen.

## Alcance

- identidad canónica;
- escudos o fallback;
- competición;
- fecha;
- favorito visible si ya existe;
- retorno al Calendario conservando contexto;
- estado de cobertura.

## Reutilización

- ruta de detalle existente;
- navegación cliente existente;
- componente de equipos/escudos existente;
- favoritos existentes;
- Madrid Time;
- contexto de retorno V940 cuando sea compatible.

## Datos

- match ID;
- team IDs;
- competition ID;
- kickoff;
- source;
- certification state.

## Aceptación

- partido correcto;
- no duplicación de cabecera;
- fallback honesto;
- retorno a fecha, filtros y posición;
- cliente/admin separados;
- FREE funcional.

## QA

- desktop/móvil;
- nombres largos;
- escudos ausentes;
- competición ausente;
- fecha inválida;
- ruta dinámica;
- 404 segura;
- teclado y foco.

## Sentinel

Detecta:

- identidad sin ID;
- fecha sin Madrid Time;
- cabecera duplicada;
- escudo roto sin fallback;
- pérdida de retorno.

## Rollback

Restaurar la cabecera anterior conservando ruta y datos.

## Fuera de alcance

- marcador;
- timeline;
- SHARK;
- Telegram;
- picks.

---

# 4. Sprint 2: Marcador, estado, fase y frescura

## Objetivo

Establecer la verdad actual del partido.

## Resultado de usuario

El usuario sabe:

- si el partido está programado, live o final;
- si el marcador es real;
- qué fase está confirmada;
- cuándo se actualizó;
- si la lectura está stale.

## Alcance

- lifecycle canónico;
- marcador;
- minuto o fase;
- frescura;
- próxima revisión;
- estados programado, live, descanso, final, aplazado y suspendido.

## Reutilización

- false-live filtering;
- stale-data filtering;
- realtime sports engine;
- sports-metrics contract;
- Madrid Time;
- estados y badges canónicos.

## Aceptación

- cero falsos live;
- cero stale presentado como actual;
- marcador solo con evidencia;
- minuto solo con evidencia;
- finalizado no vuelve a próximo;
- fase legible;
- mismo estado en página y API.

## QA

- próximo;
- live válido;
- live sin minuto;
- descanso;
- final;
- aplazado;
- suspendido;
- stale;
- cobertura insuficiente.

## Sentinel

Detecta:

- fase incoherente;
- marcador sin fuente;
- minuto inventado;
- stale público;
- divergencia entre consumidores.

## Rollback

Volver a la representación anterior del estado sin modificar lifecycle ni DB.

## Fuera de alcance

- eventos;
- estadísticas;
- participantes;
- criterio.

---

# 5. Sprint 3: Qué cambió y estados seguros

## Objetivo

Evitar que una visita de retorno obligue a releer todo.

## Resultado de usuario

El usuario entiende:

- qué cambió;
- qué sigue vigente;
- qué quedó bloqueado;
- cuál es la siguiente evidencia relevante.

## Alcance

- resumen de cambio;
- comparación con última lectura local o snapshot permitido;
- estado vacío;
- stale;
- corrección de proveedor;
- próxima actualización;
- continuidad sin tracking invasivo.

## Reutilización

- snapshot canónico;
- estados de evidencia;
- sesión o almacenamiento local permitido;
- patrones de empty state;
- Company Intelligence sin PII.

## Aceptación

- no inventa cambio;
- no confunde ausencia con cero;
- no guarda PII innecesaria;
- explica stale;
- funciona en primera visita;
- funciona si no hay cambios.

## QA

- primera visita;
- retorno sin cambio;
- retorno con cambio;
- evento corregido;
- fuente stale;
- sesión nueva;
- móvil y desktop.

## Sentinel

Detecta:

- cambio sin evidencia;
- estado vacío sin explicación;
- stale sin edad;
- tracking no permitido.

## Rollback

Ocultar el resumen de cambio y conservar identidad y estado de Sprint 2.

---

# 6. Sprint 4: Timeline de hechos

## Objetivo

Incorporar la fortaleza de la alternativa B como módulo canónico, no como arquitectura universal.

## Resultado de usuario

El usuario comprende:

- qué ocurrió;
- cuándo;
- quién participó;
- qué evento es nuevo;
- qué corrección se produjo.

## Alcance

- inicio;
- descanso;
- reanudación;
- final;
- goles;
- tarjetas;
- sustituciones;
- penaltis;
- VAR;
- incidencias oficiales cuando existan;
- dedupe;
- orden;
- agrupación.

## Reutilización

- eventos actuales;
- IDs de partido y jugador;
- formateador Madrid;
- componentes de timeline existentes;
- iconos existentes.

## Aceptación

- orden correcto;
- dedupe;
- corrección trazable;
- no filler;
- no eventos inferidos;
- timeline vacío seguro;
- volumen grande utilizable.

## QA

- sin eventos;
- un evento;
- eventos simultáneos;
- corrección;
- evento duplicado;
- partido largo;
- extra time;
- móvil;
- reduced motion.

## Sentinel

Detecta:

- duplicado;
- orden imposible;
- evento sin partido;
- actor inexistente;
- filler;
- evento futuro.

## Rollback

Retirar timeline manteniendo marcador y estado.

---

# 7. Sprint 5: Estadísticas útiles

## Objetivo

Mostrar únicamente estadísticas que respondan preguntas del partido.

## Resultado de usuario

El usuario distingue:

- valor;
- periodo;
- equipo;
- frescura;
- cobertura;
- limitación.

## Alcance

- estadísticas esenciales;
- periodo;
- comparabilidad;
- explicación de ausencia;
- actualización estable;
- hogares canónicos.

## Reutilización

- datos estadísticos existentes;
- tablas o comparadores accesibles;
- contratos de frescura;
- formato numérico existente.

## Aceptación

- cero no sustituye ausencia;
- misma métrica tiene misma definición;
- no se repite en SHARK;
- no hay overflow;
- lectura alternativa móvil;
- cambios no desplazan contenido.

## QA

- datos completos;
- parciales;
- ausentes;
- cero real;
- valores largos;
- móvil;
- teclado;
- lector de pantalla.

## Sentinel

Detecta:

- cero falso;
- definición divergente;
- periodo ausente;
- stale;
- duplicación.

## Rollback

Ocultar estadísticas sin afectar timeline ni estado.

---

# 8. Sprint 6: Alineaciones, suplentes y entrenadores

## Objetivo

Explicar quién participa y cómo cambia la estructura humana del partido.

## Resultado de usuario

El usuario distingue:

- alineación pendiente;
- probable;
- confirmada;
- titulares;
- suplentes;
- entradas y salidas;
- entrenadores confirmados.

## Alcance

- titulares;
- suplentes;
- roles cuando existen;
- sustituciones vinculadas;
- entrenadores;
- estado de confirmación;
- cobertura.

## Reutilización

- IDs de equipo/jugador;
- datos de alineación existentes;
- timeline de sustituciones;
- fallbacks de avatar/escudo;
- estados seguros.

## Aceptación

- probable nunca aparece como confirmada;
- no infiere posición;
- sustitución enlaza participantes válidos;
- ausencias explícitas;
- usable con plantillas largas;
- FREE conserva hechos confirmados.

## QA

- sin alineación;
- probable;
- confirmada;
- un equipo incompleto;
- suplentes ausentes;
- nombres largos;
- sustituciones;
- móvil.

## Sentinel

Detecta:

- estado mal etiquetado;
- jugador duplicado;
- jugador en ambos equipos;
- sustitución incoherente;
- dato inventado.

## Rollback

Retirar participantes y conservar timeline/estado.

---

# 9. Sprint 7: Contexto oficial y deportivo

## Objetivo

Integrar la profundidad del dossier sin convertirla en la arquitectura principal.

## Resultado de usuario

El usuario consulta contexto solo cuando resuelve una pregunta.

## Alcance

- árbitro;
- estadio;
- forma;
- H2H comparable;
- clasificación;
- lesiones y ausencias con fuente;
- situación competitiva;
- muestra y limitaciones.

## Reutilización

- datos de competición existentes;
- histórico;
- match lifecycle;
- sports metrics;
- componentes de contexto existentes.

## Aceptación

- muestra visible;
- H2H no determinista;
- lesión no inferida;
- clasificación verificable;
- datos ausentes omitidos o explicados;
- sin repetición.

## QA

- cobertura completa;
- parcial;
- sin árbitro;
- sin estadio;
- sin H2H comparable;
- liga;
- copa;
- eliminatoria;
- móvil.

## Sentinel

Detecta:

- muestra ausente;
- lesión inferida;
- tabla incompleta presentada como total;
- H2H sin comparabilidad;
- contexto stale.

## Rollback

Retirar contexto avanzado y conservar núcleo del partido.

---

# 10. Sprint 8: Conexiones del Sports Entity Model

## Objetivo

Preparar relaciones canónicas sin implementar todavía Team, Competition o Player Center.

## Resultado de usuario

El usuario reconoce entidades relacionadas y puede navegar solo cuando el destino existe y tiene cobertura.

## Alcance

- referencias de equipo;
- competición;
- jugador;
- IDs canónicos;
- contexto de retorno;
- destinos habilitados solo si existen;
- estado “cobertura limitada”.

## Reutilización

- rutas existentes;
- navegación segura;
- IDs canónicos;
- fallbacks;
- auditoría de enlaces.

## Aceptación

- ningún botón sin destino;
- ninguna ruta futura inventada;
- retorno preservado;
- dedupe de entidad;
- cliente/admin separados;
- compatibilidad con futura capa de entidades.

## QA

- destino existente;
- destino ausente;
- entidad duplicada;
- jugador sin cobertura;
- retorno;
- 404;
- enlaces;
- móvil.

## Sentinel

Detecta:

- ID inconsistente;
- enlace roto;
- destino no autorizado;
- pérdida de retorno;
- duplicación.

## Rollback

Desactivar enlaces profundos sin alterar el contenido del partido.

---

# 11. Sprint 9: SHARK contextual

## Objetivo

Incorporar criterio únicamente cuando responde una pregunta y existe evidencia.

## Resultado de usuario

El usuario entiende:

- evidencia;
- lectura;
- contraargumento;
- riesgo;
- invalidadores;
- limitación;
- próxima revisión.

## Alcance

- SHARK por fase;
- recomendación de esperar;
- silencio útil;
- evidencia enlazada a hogares canónicos;
- acceso por membresía;
- timestamp y versión.

## Reutilización

- SHARK safe mode;
- learning governance;
- Índice de Confianza;
- pipeline de picks;
- componentes SHARK existentes.

## Aceptación

- no repite estadísticas;
- no inventa;
- no garantiza;
- no presiona;
- puede quedar ausente;
- FREE sigue comprendiendo el partido;
- PRO/ELITE reciben profundidad real.

## QA

- evidencia suficiente;
- insuficiente;
- stale;
- hipótesis invalidada;
- sin pick;
- FREE;
- PRO;
- ELITE;
- móvil.

## Sentinel

Detecta:

- SHARK sin fuente;
- opinión presentada como hecho;
- limitación ausente;
- promesa;
- duplicación;
- respuesta genérica.

## Rollback

Retirar SHARK contextual y conservar el Match Center deportivo completo.

---

# 12. Sprint 10: Pick dentro del partido

## Objetivo

Integrar un pick publicable como expediente profesional subordinado al partido.

## Resultado de usuario

El usuario conoce:

- mercado;
- selección;
- cuota;
- frescura;
- estado;
- revisión;
- razones;
- riesgo;
- invalidadores.

## Alcance

- pick validado;
- lifecycle;
- cuota;
- estado previo/live/final;
- liquidación cuando corresponda;
- membresía;
- ausencia segura.

## Reutilización

- pick intelligence pipeline;
- odds freshness;
- grading;
- dedupe;
- track record;
- componentes de pick existentes.

## Aceptación

- pick completo;
- cuota mayor que cero;
- cuota con timestamp;
- stale bloqueado;
- no retrospectivo;
- no se publica si falta evidencia;
- resultado verificable.

## QA

- sin pick;
- candidato;
- publicable;
- stale;
- expirado;
- invalidado;
- graded;
- FREE/PRO/ELITE.

## Sentinel

Detecta:

- pick incompleto;
- cuota inválida;
- stale activo;
- duplicado;
- resultado incoherente;
- acceso incorrecto.

## Rollback

Ocultar el módulo de pick sin afectar el partido ni SHARK.

---

# 13. Sprint 11: Bankroll voluntario

## Objetivo

Mostrar exposición y límites personales sin mover dinero ni fomentar volumen.

## Resultado de usuario

El usuario comprende:

- exposición abierta;
- límite;
- concentración;
- escenario orientativo;
- opción de pausa.

## Alcance

- bankroll configurado;
- unidades;
- exposición;
- límites;
- concentración;
- modo pausa;
- recursos responsables.

## Reutilización

- datos de bankroll existentes, si están certificados;
- membresía;
- pick real;
- controles responsables.

## Aceptación

- opt-in;
- no ejecuta;
- no mueve dinero;
- no aumenta stake;
- no recupera pérdidas;
- no aparece sin configuración;
- privacidad preservada.

## QA

- no configurado;
- configurado;
- límite alcanzado;
- concentración;
- pick cerrado;
- modo pausa;
- móvil.

## Sentinel

Detecta:

- stake automático;
- movimiento de dinero;
- límite ignorado;
- presión;
- exposición incorrecta;
- PII.

## Rollback

Retirar Bankroll sin alterar picks ni membresías.

---

# 14. Sprint 12: Favoritos y continuidad Telegram

## Objetivo

Permitir que el usuario deje el partido sin perder seguimiento.

## Resultado de usuario

El usuario puede:

- seguir;
- dejar de seguir;
- elegir una alerta;
- conocer el estado;
- volver al cambio correcto.

## Alcance

- favorito;
- alertas configurables;
- Telegram opt-in;
- dedupe;
- horario Madrid;
- límites;
- retorno contextual;
- estado de entrega seguro.

## Reutilización

- favoritos existentes;
- Telegram intelligence;
- membership variants;
- dedupe;
- safe links;
- preferencias.

## Aceptación

- no envío sin opt-in;
- no duplicados;
- no filler;
- no IDs privados visibles;
- destino correcto;
- control de frecuencia;
- FREE/PRO/ELITE coherentes.

## QA

- sin Telegram;
- configurado;
- desactivado;
- duplicado;
- límite diario;
- mensaje bloqueado;
- cambio de membresía;
- móvil.

## Sentinel

Detecta:

- envío no autorizado;
- duplicado;
- destino incorrecto;
- CTA repetido;
- enlace roto;
- exceso de frecuencia.

## Rollback

Desactivar continuidad Telegram y conservar favorito local.

---

# 15. Sprint 13: Experiencia transversal

## Objetivo

Cerrar responsive, accesibilidad y rendimiento sin añadir funciones.

## Resultado de usuario

Match Center se siente:

- estable;
- rápido;
- comprensible;
- consistente;
- accesible;
- profesional.

## Alcance

- desktop;
- tablet;
- móvil;
- safe area;
- foco;
- teclado;
- lectores de pantalla;
- reduced motion;
- carga progresiva;
- estados de loading;
- scroll y sticky;
- memoria de posición;
- assets y fallback.

## Reutilización

- sistema visual existente;
- componentes canónicos;
- tokens;
- patrones de navegación;
- Browser QA;
- performance checks.

## Aceptación

- cero overflow;
- cero texto cortado;
- cero navegación duplicada;
- cero mezcla admin;
- foco correcto;
- actualización live no invasiva;
- núcleo no bloqueado;
- misma verdad en todos los perfiles.

## QA

- viewports oficiales;
- zoom;
- teclado;
- reduced motion;
- contenido largo;
- empty;
- stale;
- error;
- red lenta local simulada.

## Sentinel

Detecta:

- overflow;
- tamaño táctil;
- foco;
- duplicación;
- asset roto;
- layout shift;
- módulo fuera de orden.

## Rollback

Revertir ajustes transversales sin eliminar capacidades funcionales.

---

# 16. Sprint 14: Release gate y pulido final

## Objetivo

Certificar la experiencia completa sin añadir alcance.

## Alcance

- Browser QA final;
- Sentinel;
- AutoPilot;
- Company Intelligence;
- tests;
- Jinja;
- navegación;
- rutas;
- privacidad;
- Secret Guard;
- rendimiento;
- accesibilidad;
- datos;
- release audit;
- rollback.

## Aceptación

- P0 = 0;
- P1 = 0;
- MAJOR visual = 0;
- MEDIUM corregible = 0;
- 5xx = 0;
- false live = 0;
- stale público = 0;
- datos inventados = 0;
- links rotos = 0;
- secretos = 0;
- rollback probado localmente;
- producción no declarada sin deploy.

## Browser QA

Estados mínimos:

- previa;
- alineaciones pendientes;
- alineaciones confirmadas;
- live;
- descanso;
- final;
- aplazado;
- stale;
- cobertura insuficiente;
- FREE;
- PRO;
- ELITE;
- desktop;
- móvil.

## Rollback

Restaurar el último Match Center certificado sin tocar DB, usuarios, pagos o Telegram.

## Fuera de alcance

- Team Center;
- Competition Center;
- Player Center;
- Sports Hub;
- nuevas funciones.

---

# 17. Matriz de despliegue independiente

| Sprint | Entrega autónoma | Dependencia | Fallback |
|---:|---|---|---|
| 1 | Identidad y retorno | Ruta actual | Cabecera anterior |
| 2 | Estado y marcador | Sprint 1 | Estado anterior |
| 3 | Cambio y safe mode | Sprint 2 | Sin resumen de cambio |
| 4 | Timeline | Sprint 3 | Estado sin timeline |
| 5 | Estadísticas | Sprint 2 | Sin estadísticas |
| 6 | Participantes | Sprint 2 | Estado pendiente |
| 7 | Contexto | Sprint 2 | Núcleo sin contexto avanzado |
| 8 | Entidades | Sprint 1 | Texto sin enlace |
| 9 | SHARK | Sprints 2-7 | Partido sin SHARK |
| 10 | Pick | Sprints 2 y 9 | Partido sin pick |
| 11 | Bankroll | Sprint 10 | Sin Bankroll |
| 12 | Continuidad | Sprints 1-3 | Favorito local o sin alerta |
| 13 | Calidad transversal | Sprints 1-12 | Último layout certificado |
| 14 | Release gate | Todos | Último release certificado |

---

# 18. Reglas de no expansión

Durante la implementación de Match Center no se debe:

- crear Team Center;
- crear Competition Center;
- crear Player Center;
- rehacer Calendario;
- rediseñar SHARK global;
- rediseñar Telegram global;
- crear Sports Hub;
- cambiar precios;
- cambiar membresías;
- añadir proveedores;
- migrar DB sin necesidad;
- crear rutas paralelas;
- duplicar componentes.

Los hallazgos ajenos se documentan y permanecen fuera del Sprint.

---

# 19. Estado final

`BACKLOG_APPROVED`

`SPRINTS_DEFINED = 14`

`EACH_SPRINT_DEPLOYABLE = TRUE`

`IMPLEMENTATION_STARTED = FALSE`

`CODE_MODIFIED = FALSE`

`PRODUCTION_MODIFIED = FALSE`

Siguiente acción autorizable:

> Crear la especificación técnica del Sprint 1, Identidad estable y retorno, sin implementar hasta su aprobación.

