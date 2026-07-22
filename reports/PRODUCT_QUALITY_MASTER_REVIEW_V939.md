# PRODUCT QUALITY MASTER REVIEW V939

## 1. Decisión de esta fase

**Estado:** auditoría terminada; P1 funcional y primer sprint P2 resueltos y validados localmente. PQV939-003 continúa bloqueado por cobertura; los demás P2 y todos los P3 permanecen abiertos.

Este documento convierte el vídeo `NeMeSiS SHARK PRO - Google Chrome 2026-07-22 14-26-39.mp4` en evidencia oficial de producto para el recorrido que realmente contiene. Tras cerrar P1 se ejecutó exclusivamente PQV939-004: contrato de rail acotado y recuperación del ancho útil en Partidos, Inicio y Telegram. No se inició ningún otro P2/P3; este sprint no ejecutó deploy ni certificó producción.

La grabación permite auditar con detalle el cliente web de escritorio y la home pública. No contiene vistas móviles ni pantallas de administración. Por tanto, no permite certificar CEO Dashboard, Operations Center, Recovery Simulator, Experiments, Company Intelligence, Sentinel o AutoPilot. Esas áreas quedan expresamente **NO OBSERVABLES EN EL VÍDEO**, no aprobadas ni suspendidas.

## 2. Evidencia y método

| Campo | Evidencia |
|---|---|
| Vídeo | `C:\Users\aloha\Videos\Captures\NeMeSiS SHARK PRO - Google Chrome 2026-07-22 14-26-39.mp4` |
| SHA-256 | `E223BDC68BB98C18BCF5C7EB9A6F089F3BA0B1B2DE703078D33EE4FE2E8AEEDF` |
| Duración | 04:30 |
| Resolución | 1360 x 720 |
| Contexto | Chrome, escritorio, cuenta cliente autenticada y posterior cierre de sesión |
| Versión local al auditar | `V939_AUTONOMOUS_COMPANY_INTELLIGENCE_GROWTH_AND_QUALITY_PLATFORM_FINAL` |
| Muestreo | 284 fotogramas, aproximadamente uno cada 0,954 s; revisión adicional de fotogramas completos en transiciones y defectos |
| Audio | No utilizado como evidencia de interfaz |
| Evidencia complementaria | Lectura local, sin ejecución ni cambios, de templates y CSS relacionados para confirmar causas raíz |

### Estados de certeza

- **CONFIRMADO EN VÍDEO:** el síntoma es visible de forma inequívoca.
- **CAUSA CONFIRMADA EN CÓDIGO:** el patrón exacto que produce el síntoma está localizado.
- **CAUSA PROBABLE:** el vídeo demuestra el defecto, pero la causa completa requiere runtime o datos.
- **NO OBSERVABLE:** la grabación no contiene evidencia suficiente.
- **NO CERTIFICADO:** no puede aprobarse con este material.

### Escala de gravedad

- **P0:** caída, pérdida de datos, seguridad o daño económico inmediato.
- **P1:** confianza o tarea principal gravemente afectada; bloquea una certificación de producto completa.
- **P2:** fricción material, densidad deficiente o lenguaje que reduce calidad percibida.
- **P3:** detalle de consistencia o pulido sin bloqueo funcional.

## 3. Inventario cronológico del vídeo

| Inicio | Fin | Pantalla | Ruta inferida/visible | Ámbito | Objetivo | Módulos visibles | Acciones visibles |
|---:|---:|---|---|---|---|---|---|
| 00:00.0 | 00:09.5 | Inicio cliente, cabecera | `/app` | Cliente autenticado | Situar al usuario y priorizar su jornada | Saludo, plan, hora Madrid, estado deportivo, fuente, decisión principal | Ver partidos, revisar directo, navegación principal |
| 00:09.5 | 00:19.0 | Inicio cliente, contenido | `/app` | Cliente autenticado | Guiar desde agenda hacia picks y SHARK | KPIs, ruta recomendada, pick destacado vacío, próximos partidos, SHARK y Telegram | Ver todos, revisar picks, consultar SHARK, abrir Telegram |
| 00:19.0 | 00:24.8 | Inicio cliente, accesos y retorno | `/app` | Cliente autenticado | Acceso a áreas y valor de membresía | Accesos rápidos, recorrido FREE/PRO/ELITE, footer; retorno arriba | Calendario, Directo, Telegram, Histórico, Mi cuenta, Membresías |
| 00:24.8 | 00:31.0 | Partidos, cabecera y filtros | `/calendar` | Cliente autenticado | Presentar agenda real y filtros | Cabecera, barra de sincronización, ciclo de vida, decisión, KPIs, tabs y filtros | Ir a directo, ver picks, aplicar filtros, cambiar rango |
| 00:31.0 | 01:31.0 | Partidos, primer bloque | `/calendar` | Cliente autenticado | Mostrar partidos de hoy agrupados | Grupo Hoy, liga, tarjetas de partido, estado del proveedor, cambio de fecha | Ver partido, filtros, accesos laterales |
| 01:31.0 | 02:06.8 | Partidos, lista extensa y pie | `/calendar` | Cliente autenticado | Recorrer la agenda completa | Muchas ligas y tarjetas, confianza del dato, procedencia, footer | Ver partido en cada tarjeta |
| 02:06.8 | 02:13.0 | Directo, cabecera | `/live` | Cliente autenticado | Informar si existe actividad real | Barra de sincronización, ciclo de vida, estado vacío, KPIs y filtros | Abrir calendario, ver picks |
| 02:13.0 | 02:20.2 | Directo, board y próximos | `/live` | Cliente autenticado | Mantener utilidad cuando no hay directos | Board vacío honesto, próximos encuentros, contrato del dato, proveedor | Ver próximos partidos, abrir calendario |
| 02:20.2 | 02:25.0 | Picks, cabecera | `/picks` | Cliente autenticado | Explicar por qué no hay una decisión publicable | Fuente, barra de datos, decisión, KPIs, tabs | Histórico, consultar SHARK, ver calendario |
| 02:25.0 | 02:41.2 | Picks, detalle vacío | `/picks` | Cliente autenticado | Mostrar la puerta de calidad | Pick destacado vacío, por qué/riesgo/recomendación, reglas, más picks, juego responsable | Ver calendario, explicar con SHARK |
| 02:41.2 | 02:49.0 | Histórico, recorrido | `/track-record` | Cliente autenticado | Explicar la falta de muestra evaluable | Estado seguro, KPIs, filtros, evolución real vacía, picks cerrados, regla de confianza | Ver picks activos, entender SHARK |
| 02:49.0 | 03:00.3 | Histórico, cabecera estable | `/track-record` | Cliente autenticado | Mantener transparencia sobre ROI y resultados | Mismos módulos de histórico sin datos decorativos | Ver picks |
| 03:00.3 | 03:13.0 | SHARK, modo seguro | `/shark` | Cliente autenticado | Definir capacidad y límites de SHARK | Hero, modo seguro, fuente, por qué/riesgo/recomendación, acción principal | Explorar partidos, ver directo, revisar picks |
| 03:13.0 | 03:19.0 | SHARK, respuesta y contexto | `/shark` | Cliente autenticado | Responder con datos disponibles y límites | KPIs, respuesta actual, capacidades, preguntas rápidas, estado del contexto | Preguntas rápidas, partidos, picks, directo, Telegram, soporte |
| 03:19.0 | 03:28.0 | SHARK, retorno superior | `/shark` | Cliente autenticado | Reforzar el modo seguro y la siguiente acción | Hero y bloques de criterio | Explorar partidos |
| 03:28.0 | 03:33.0 | Telegram, cabecera | `/telegram` | Cliente autenticado | Explicar el canal y la vinculación | Hero, flujo protegido, estado de conexión, plan | Empezar vinculación, ver qué recibiré, mi cuenta |
| 03:33.0 | 03:46.1 | Telegram, configuración | `/telegram` | Cliente autenticado | Guiar una conexión segura | Beneficios, tres pasos, código de vinculación, confianza y calidad | Conectar Telegram, generar nuevo código, revisar pasos |
| 03:46.1 | 03:50.0 | Cuenta, cabecera | `/profile` | Cliente autenticado | Resumir identidad, plan y siguiente mejora | Usuario, plan, sesión, Telegram, KPIs | Gestionar plan, vincular Telegram |
| 03:50.0 | 04:08.9 | Cuenta, servicios y actividad | `/profile` | Cliente autenticado | Gestionar servicios, seguridad y actividad | Cuenta y servicios, estado, actividad, documentos, logout, valor del plan | Telegram, favoritos, seguridad, soporte, términos, privacidad, reembolsos, cerrar sesión |
| 04:08.9 | 04:20.0 | Home pública tras logout | `/` | Público | Comunicar propuesta de valor y llevar a registro o exploración | Hero, Hoy en NeMeSiS, CTA, datos, radar, partidos, recorrido, confianza, planes, responsabilidad | Crear cuenta, entrar, explorar radar, ver partido, SHARK, comparar planes |
| 04:20.0 | 04:30.0 | Sitio externo | Fuera de NeMeSiS | Excluido | No pertenece al producto | Reproductor de radio externo | Excluido de la auditoría |

## 4. Mapa de navegación observado

```text
/app
  -> Partidos (topbar) -> /calendar
  -> Directo (topbar) -> /live
  -> Picks (topbar) -> /picks
  -> Histórico (topbar) -> /track-record
  -> SHARK (topbar) -> /shark
  -> Telegram (topbar) -> /telegram
  -> Cuenta (topbar) -> /profile
  -> Cerrar sesión -> /
```

### Navegación global autenticada observada

`Inicio | Partidos | Directo | Picks | Histórico | SHARK | Telegram | Cuenta`

- El estado activo se distingue correctamente.
- Cliente y administración no se mezclan en el recorrido grabado.
- Las rutas observadas cargan sin 404 ni 500 visibles.
- No se observan breadcrumbs; la topbar proporciona la orientación principal.
- El flujo Partidos -> Directo -> Picks -> Histórico -> SHARK -> Telegram -> Cuenta es comprensible y no presenta pantallas redundantes demostradas.

### Navegación pública observada

`Inicio | Partidos | Directo | Picks | Histórico | SHARK | Entrar | Crear cuenta`

- El cierre de sesión desemboca en la home pública.
- La home conserva acceso al producto y a autenticación.
- No se certifica el destino de todos los CTA porque el vídeo no los pulsa.

### Cobertura de navegación no disponible

- No se abre detalle de partido.
- No se abre Membresías.
- No se abre Soporte, login, registro, 404 o 500.
- No se abre ninguna ruta admin.
- No existe evidencia móvil ni bottom navigation.

## 5. Baseline de calidad que debe preservarse

1. Branding consistente: logo, azul oscuro, azul eléctrico, cian y dorado mantienen una identidad clara.
2. Topbar estable: no hay duplicación visible ni mezcla entre cliente y admin.
3. Empty states honestos: Live, Picks e Histórico no fabrican actividad, pick ni rentabilidad.
4. SHARK comunica límites: muestra “Modo seguro activo” y “IA avanzada no configurada”.
5. Juego responsable visible: no se prometen beneficios ni resultados.
6. Estados activos y CTA principales se distinguen con claridad.
7. No se observa overflow horizontal de página a 1360 x 720.
8. Los escudos visibles cargan correctamente y los fallbacks no dominan la experiencia.
9. El cierre de sesión está visible, separado y contextualizado.
10. La home pública explica qué hace el producto y ofrece una siguiente acción clara.

## 6. Diseño aprobado para la iteración P1

### P1.1 — Contrato único de métricas deportivas

**Origen actual:** `get_public_home_sports_summary()` ya es la lectura validada y cacheada de DB/caché. Sin embargo, `calendar.html` consume sus conteos de calendario, la barra realtime vuelve a derivar un agregado de hoy más próximos, `live.html` usa la longitud del filtro activo como si fuese el total de hoy y `shark_briefing()` ejecuta una consulta heredada independiente.

**Diferencias demostradas:** `Partidos hoy`, `partidos disponibles`, `live confirmado`, `picks completos` y `finalizados` no comparten nombre, scope ni snapshot. Una cifra válida para un filtro termina presentada como si fuese una métrica global.

**Causa raíz:** existen varios consumidores que vuelven a contar colecciones ya validadas. El dato de origen es común en parte del recorrido, pero no existe un contrato explícito que impida reinterpretarlo.

**Propuesta aprobada:** reutilizar el resumen existente y publicar un único objeto `sports_metrics` por petición con estas definiciones:

- `matches_today`: partidos completos de hoy visibles en la agenda, incluidos los directos con evidencia fresca;
- `matches_available`: unión deduplicada de partidos completos de hoy y próximos;
- `live_confirmed`: directos con marcador, minuto o fase real y frescura válida;
- `picks_ready`: picks completos y publicables;
- `finished_verified`: resultados finalizados y verificables de hoy;
- `incomplete_excluded` y `stale_live_excluded`: exclusiones trazables que nunca entran en los KPI públicos;
- `snapshot_id`, `scope`, `generated_at_madrid`, `last_sync` y `source`: identidad y alcance del contrato.

Calendario, Directo, Picks, SHARK, Dashboard, home y barra realtime deben leer ese mismo objeto. Los filtros pueden cambiar las tarjetas visibles, pero no redefinir una métrica global.

**Impacto esperado:** elimina contradicciones visibles sin relajar la puerta de datos, evita consultas deportivas duplicadas en SHARK y permite que Sentinel compare rutas por identidad de snapshot y definición, no por texto aproximado.

**Riesgo controlado:** no se ocultan partidos válidos; solo quedan fuera los registros incompletos y los live stale ya bloqueados por V937. Los conteos de semana, favoritos y filtros siguen siendo métricas locales claramente etiquetadas.

### P1.2 — Contrato de la tarjeta canónica de partido

**Origen actual:** `match_card()` es compartida, pero el grid fuerza tres columnas incluso dentro del layout con rail. El footer mezcla señales, procedencia, favorito y CTA en una sola fila flexible sin reserva de anchura.

**Diferencias demostradas:** a unos 290 px de ancho lógico se parten estados, procedencia y `Ver partido`; la altura depende del wrapping accidental y la alineación cambia entre filas.

**Causa raíz:** el componente no define zonas internas estables y el grid responde al viewport, no al ancho real disponible.

**Propuesta aprobada:** conservar un único macro y dividirlo en cabecera, equipos y footer con dos zonas explícitas: señales y acciones. Usar tres columnas solo a ancho completo, dos dentro de un layout con rail y una en móvil. CTA, chips y palabras no pueden partirse; la card mantiene filas lógicas iguales y permite que nombres de equipo largos envuelvan de forma natural.

**Impacto esperado:** lectura rápida, CTA estable y altura coherente en Home, Dashboard, Partidos y los próximos de Directo, sin crear variantes visuales desconectadas.

**Riesgo controlado:** el cambio queda limitado al macro canónico y a sus selectores existentes. No modifica el rail, la densidad del calendario, el copy ni otros defectos P2/P3.

### 6.3 — Sports Data Contract oficial (`sports-metrics-v1`)

**Estado normativo:** ACTIVO Y VALIDADO LOCALMENTE. `get_public_home_sports_summary()` es el único origen autorizado de las métricas deportivas compartidas. Cada petición reutiliza el mismo objeto `sports_metrics`; `snapshot_id` identifica el conjunto exacto de partidos y picks, no una consulta aproximada.

**Consumidores autorizados:** Inicio, Dashboard cliente, Partidos, Calendario, Live, Picks, SHARK, Telegram, CEO Dashboard, Operations Center, Company Intelligence, Sentinel y AutoPilot.

| Métrica | Definición funcional | Origen y filtros | Ventana / actualización | Limitaciones y casos borde |
|---|---|---|---|---|
| `matches_today` | Partidos completos visibles hoy, incluidos live con evidencia fresca. | Resumen canónico; completos, fuente real, fecha Madrid de hoy, live no stale. | Día actual Europe/Madrid; caché local 15 s. | No incluye incompletos ni live stale. Un finalizado de hoy puede pertenecer también a `finished_verified`. |
| `matches_available` | Unión deduplicada de partidos completos de hoy y próximos. | Resumen canónico; completos, fuente real, hoy o próximos, dedupe y exclusión stale. | Ventana de agenda presente en DB/caché; 15 s. | Depende de la cobertura sincronizada. Un live ya presente en agenda cuenta una vez. |
| `live_confirmed` | Directos con marcador, minuto o fase explícita real y frescura válida. | Resumen canónico; evidencia live y antigüedad máxima de 120 s. | Estado live actual; 15 s. | Una etiqueta LIVE genérica no es evidencia. Al quedar stale se excluye, no se transforma en programado ficticio. |
| `picks_ready` | Picks activos con partido, mercado, selección, cuota y estado publicable válidos. | Resumen canónico; pick completo, publicable, dentro de ventana y partido no stale. | Ventana pública activa; 15 s. | Excluye candidatos, bloqueados, duplicados y cerrados. Varios picks del mismo partido cuentan por separado. |
| `matches_with_picks` | Partidos únicos vinculados a uno o más picks publicables. | Resumen canónico; `match_id` válido y dedupe por partido. | Ventana pública activa; 15 s. | No equivale al número total de picks. Varios picks de un partido cuentan como un partido. |
| `finished_verified` | Partidos de hoy finalizados con resultado verificable. | Resumen canónico; completo, fecha Madrid de hoy, lifecycle finalizado y ambos marcadores presentes. | Día actual Europe/Madrid; 15 s. | No es el histórico total. Un resultado pendiente permanece fuera hasta ser verificable. |
| `matches_synchronized` | Registros deportivos leídos del almacenamiento local para el snapshot. | Resumen canónico; lectura DB/caché local previa a filtros públicos. | Último snapshot local; 15 s. | Es métrica operativa y puede incluir registros excluidos. DB bloqueada devuelve estado seguro, nunca una estimación. |
| `incomplete_excluded` | Registros sin campos deportivos esenciales apartados de superficies públicas. | Resumen canónico; falta competición, fecha, hora, equipos o fuente real. | Último snapshot local; 15 s. | Solo para CEO, Operations, Company Intelligence, Sentinel y AutoPilot. Reingresa cuando completa todos los campos. |
| `stale_live_excluded` | Registros live cuya evidencia supera la frescura válida. | Resumen canónico; lifecycle live/descanso y antigüedad superior a 120 s. | Estado live actual; 15 s. | No afirma que haya finalizado. Queda fuera de cards, badges, KPIs, APIs públicas, Telegram y SHARK hasta nueva evidencia. |

#### Invariantes obligatorias

1. Una superficie puede filtrar sus tarjetas, pero no redefinir ninguna métrica del contrato ni reutilizar su etiqueta para contar el filtro local.
2. Todo consumidor visual expone `data-sports-contract` y `data-sports-snapshot`; los siete conteos públicos deben coincidir con el snapshot recibido.
3. Ningún consumidor autorizado puede llamar por su cuenta a `get_matches`, `get_upcoming_matches`, `get_picks`, `rows`, `one` ni ejecutar agregados SQL deportivos.
4. El render no llama proveedores externos ni escribe la DB. El contrato procede exclusivamente de DB/caché y conserva `last_sync`, `generated_at_madrid`, fuente, alcance y exclusiones.
5. En DB bloqueada o sin datos se entrega un snapshot seguro con cero reales y estado explícito; nunca se estima ni se rellena.
6. Los conteos locales de semana, mañana, favoritos o resultados de búsqueda siguen permitidos si se etiquetan como filtro local y no sustituyen una métrica oficial.

#### Por qué divergía antes y qué riesgo se elimina

Antes, Calendario consumía el resumen validado, Live contaba el subconjunto filtrado, SHARK consultaba partidos por separado y otras barras agregaban hoy más próximos. El mismo término visible representaba alcances y momentos distintos. El contrato elimina contradicciones de confianza, dobles consultas, falsos live y decisiones de SHARK/Telegram basadas en un conjunto diferente al mostrado al cliente.

#### Sentinel y AutoPilot

- Sentinel compara contrato, `snapshot_id` y valores renderizados en cada ruta; una ausencia o diferencia abre una incidencia `sports_data_contract` de severidad alta/P1.
- Sentinel analiza el AST de los consumidores autorizados. Si reaparece una consulta o agregado privado, abre P1 aunque la cifra coincida por casualidad.
- AutoPilot transforma la incidencia en tarea y prompt trazables, siempre `pending_approval`; no puede autoaplicar cambios de datos, rutas o consultas.
- La política queda expuesta como `independent_queries_forbidden=true`, `violation_priority=P1` y `autofix_allowed=false`.

### 6.4 — Especificación oficial de la tarjeta canónica de partido

**Identidad:** existe un único macro `match_card()` y toda instancia declara `data-v939-match-card-spec="canonical-v1"`. Ninguna pantalla puede crear otra estructura sin una decisión de producto documentada y una nueva prueba visual.

| Aspecto | Especificación obligatoria |
|---|---|
| Estructura | `article` canónico con tres zonas: cabecera, equipos y footer. El footer se divide en señales y acciones; no se mezclan en una fila improvisada. |
| Jerarquía | Competición y hora arriba; equipos/escudos/marcador como foco; estado, prioridad y procedencia antes de favorito/CTA. |
| Altura mínima | 178 px en escritorio amplio para la variante no compacta. En móvil prevalece el contenido y la zona táctil, sin forzar hueco artificial. |
| Altura máxima | No se fija un máximo arbitrario: la competencia y cada equipo quedan limitados a dos líneas, y el footer envuelve por bloques. La card nunca recorta una acción. |
| Wrapping | Competición y nombres admiten como máximo dos líneas naturales. Se prohíben `overflow-wrap:anywhere` y `word-break:break-all`. CTA, estado y prioridad no parten palabras. |
| Chips y badges | Pueden pasar a la siguiente línea como unidades completas dentro de `signals`; no invaden `actions` ni ensanchan la página. |
| Botones | `Ver partido` permanece en una línea. A 430 px o menos la zona de acciones ocupa una fila propia y el CTA se expande de forma deliberada. |
| Desktop | Grid completo: hasta tres columnas. Dentro de `.v933-two-col`: exactamente dos columnas. Las cards de una misma fila se estiran a la misma altura lógica. |
| Móvil | A 800 px o menos, incluida la variante dentro de `.v933-two-col`, una sola columna. Sin scroll horizontal ni cards estrechas paralelas. |
| Estados | Completa, incompleta, stale y live conservan la misma estructura; cambia el mensaje/tono, no la geometría básica. Minuto o marcador solo aparecen con evidencia real. |
| Variantes | `compact` y el wrapper `live_card` pueden reducir densidad, pero reutilizan el mismo macro, zonas, atributos y reglas de wrapping. |

#### Prevención permanente

Sentinel compara el número de cards deportivas con el número de cards `canonical-v1`; cualquier diferencia abre P1. Browser QA comprueba overflow, anchura, altura por fila, footer, CTA, wrapping y límites de descendientes visibles en desktop y móvil. AutoPilot genera una tarea CSS/componente con aprobación y nunca crea automáticamente una variante.

### 6.5 — Evidencia de cierre local de P1

- Regresión específica P1: **8/8 PASS**, incluida la ejecución efectiva del guard dentro del scan de rutas.
- Suite local completa: **38/38 PASS** usando temporal aislado.
- Compilación: `py_compile` y `compileall` PASS.
- Jinja: **186 templates** parseados.
- Check V939: PASS.
- Privacy/Secret Guard: **979 archivos**, 0 secretos confirmados, 0 hallazgos de privacidad.
- Continuous Sentinel: **10.0**, 39 rutas de scan, 0 incidencias; Navigation Integrity: 695 rutas, 944 enlaces, 0 rotos y 0 bucles.
- AutoPilot diagnóstico: política P1 activa, `snapshot_id` recibido, 0 incidencias `sports_data_contract`; sus hallazgos ajenos a P1 permanecen abiertos y sin modificación.
- Verificación de imports/rutas: 648 rutas, 0 templates o assets ausentes.
- Browser QA real local: 10 capturas (`/`, `/calendar`, `/live`, `/picks`, `/shark`) en 1366x768 y 390x844; HTTP 200, un solo snapshot `2d20b0f39d6b4116`, 0 overflow, 0 navegación duplicada y 0 errores de consola.
- La copia local no contenía partidos válidos; por eso esa pasada certifica métricas y estados vacíos, no la geometría de cards.
- Arnés visual temporal y aislado: dos cards canónicas con textos largos. Desktop: 390,1 px por card, dos columnas y 240,9 px de altura igual. Móvil: 312 px por card, una columna y 258 px de altura igual. Footer, señales, CTA y palabras permanecen dentro, sin scroll horizontal.
- Capturas: `browser_qa/V939_P1/desktop_1366x768_canonical-match-card-harness.png` y `browser_qa/V939_P1/mobile_390x844_canonical-match-card-harness.png`, además de las diez rutas reales.
- La primera pasada del arnés detectó que la especificidad de `.v933-two-col .v933-match-grid` anulaba la media query móvil. Se corrigió en la regla existente y la segunda pasada quedó verde.
- El check histórico V937 solo falla por exigir literalmente identidad/caché V937 frente a la V939 vigente; no reporta una regresión deportiva.
- El navegador integrado no pudo iniciarse por ACL del entorno; Playwright local ejecutó la misma validación. Producción no fue tocada ni certificada.

**Comparación con el vídeo:** las condiciones que causaban PQV939-002 ya no se reproducen: el rail usa dos cards de anchura útil en escritorio y móvil fuerza una sola. Los términos de estado, procedencia y `Ver partido` no se fragmentan. PQV939-001 tampoco puede volver a mostrar scopes divergentes mientras los consumidores mantengan el snapshot canónico. Esta confirmación es local; no es una declaración de producción ni de pixel-perfect.

## 7. Registro completo de defectos

### P0

**No se observa ningún P0 en el vídeo.** La grabación no demuestra caída total, pérdida de datos, cobro incorrecto, exposición de secreto o acceso admin indebido.

### P1

#### PQV939-001 — Contrato de métricas deportivas incoherente entre pantallas

**Estado:** RESUELTO LOCALMENTE EN ESTA ITERACIÓN P1. Pendiente únicamente de certificación tras despliegue autorizado.

- **Pantallas y timestamps:** Partidos 00:25-02:06; Directo 02:07-02:20; SHARK 03:13-03:19; home pública 04:09-04:20.
- **Elemento:** contadores “Hoy”, “Partidos”, “Finalizados” y resumen textual de SHARK.
- **Descripción:** Partidos muestra 108 encuentros de hoy; Directo muestra 0 en “Hoy” y 27 finalizados mientras comparte una barra global de 234; SHARK afirma en su respuesta “Hoy: 155 partidos” y, a la vez, muestra 234 partidos disponibles. El paso del tiempo puede explicar la variación 108 -> 106 observada después del logout, pero no explica los alcances 0/108/155 sin una etiqueta de scope.
- **Impacto:** erosiona la confianza en el dato central del producto y dificulta saber qué cifra es canónica.
- **Causa raíz:** **CONFIRMADA EN CÓDIGO.** `calendar.html` usa el resumen validado del calendario; `live.html` construye “Hoy” con la longitud del conjunto filtrado de la vista live; `shark_briefing()` ejecuta una consulta independiente mediante `get_matches(today_iso(), "today")`. No existe un contrato único de definición y scope para el mismo concepto visible.
- **Solución:** una única fuente validada para `today_complete`, `all_available`, `live_confirmed` y `finished_verified`; cada cifra debe llevar scope explícito. SHARK debe consumir exactamente ese snapshot o mostrar la edad/alcance del suyo.
- **Complejidad:** media.
- **Riesgo de corregir:** medio; una unificación mal hecha podría ocultar partidos válidos.
- **Cómo evitar que vuelva:** incluir `summary_id`, `scope`, `generated_at_madrid` y definición en cada consumidor.
- **Check futuro:** para un mismo snapshot, Home, Partidos, Live, SHARK y API deben satisfacer invariantes de conteo y etiqueta.
- **Aprendizaje permanente:** Sentinel abre P1 si una misma métrica y snapshot difieren; AutoPilot solo propone diagnóstico; Company Intelligence registra fuente, scope y frescura, nunca corrige datos automáticamente.

#### PQV939-002 — Tarjetas de partido ilegibles en el layout real de escritorio

**Estado:** RESUELTO LOCALMENTE EN ESTA ITERACIÓN P1. Segunda pasada Browser QA verde en desktop y móvil.

- **Pantallas y timestamps:** Inicio cliente 00:11-00:18; Partidos 01:31-02:06; home pública 04:13-04:16.
- **Elemento:** match cards, footer de estado y botón “Ver partido”.
- **Descripción:** “Programado”, “Próximo”, el proveedor, “Actualizado” y “Ver partido” se parten en dos, tres o cuatro líneas. El CTA se convierte en un bloque alto y estrecho, y el pie de la tarjeta pierde jerarquía.
- **Impacto:** afecta la tarea principal del producto: escanear partidos y abrir uno. La pantalla parece comprimida y sin acabado comercial.
- **Causa raíz:** **CONFIRMADA EN CÓDIGO.** `.v933-two-col` reduce el área principal con un rail fijo; dentro de ella `.v933-match-grid` impone tres columnas. El footer usa flex sin un contrato de anchura y `.v933-action`/`.v933-status-chip` permiten wrapping. El resultado deja tarjetas de unos 290 px con más contenido del que admiten.
- **Solución:** grid adaptativo por anchura real, no por viewport; dos columnas cuando existe rail; CTA y estados en una fila o estructura apilada deliberada; palabras y CTA nunca deben romperse carácter a carácter.
- **Complejidad:** media.
- **Riesgo de corregir:** medio; afecta un componente compartido en varias rutas y móvil debe verificarse aparte.
- **Cómo evitar que vuelva:** mínimo de ancho por variante y prueba visual con nombres largos, proveedor y CTA.
- **Check futuro:** cero saltos internos en “Ver partido”, estados y procedencia a 1360/1440/1600/1920; altura consistente por fila.
- **Aprendizaje permanente:** Sentinel captura cards con más de dos líneas en CTA o palabras partidas; AutoPilot crea tarea CSS, sin autoaplicar; Company Intelligence asocia el fallo a todas las rutas que usan `match_card`.

#### PQV939-003 — El vídeo no cubre el producto completo que pretende certificar

**Estado:** ABIERTO — BLOQUEADO POR EVIDENCIA. No se ha reclasificado ni corregido en esta iteración.

- **Pantalla/timestamp:** grabación completa 00:00-04:30.
- **Elemento:** cobertura de referencia.
- **Descripción:** solo aparecen cliente desktop y home pública. No hay admin, CEO Dashboard, Operations Center, Recovery, Experiments, Company Intelligence, Sentinel, AutoPilot, detalle de partido, auth, membresías ni móvil.
- **Impacto:** impide declarar esta auditoría como certificación definitiva de “toda la aplicación”.
- **Causa raíz:** **CONFIRMADA EN EL ARTEFACTO.** La grabación no contiene esas rutas ni viewports.
- **Solución:** conservar este vídeo como referencia canónica del recorrido cliente desktop y añadir una grabación admin y otra móvil, sin sustituir la evidencia actual.
- **Complejidad:** baja.
- **Riesgo de corregir:** bajo; no requiere código.
- **Cómo evitar que vuelva:** manifiesto obligatorio de rutas/viewports antes de aceptar una grabación como referencia global.
- **Check futuro:** cobertura 100% del manifiesto de pantallas críticas, con timestamps y estado de autenticación.
- **Aprendizaje permanente:** Sentinel/Company Intelligence marcan `BLOCKED_BY_EVIDENCE` cuando falta una familia de pantallas; nunca infieren PASS por ausencia de imagen.

### P2

#### PQV939-004 — Rail lateral rígido deja grandes áreas muertas

**Estado:** RESUELTO LOCALMENTE — alcance exclusivo; ninguna otra incidencia P2/P3 forma parte de esta iteración.

**Expediente previo obligatorio (antes de código):**

- **Descripción:** el rail contextual y la colección principal comparten una rejilla que conserva ambas columnas durante toda su altura. Cuando el rail termina, la colección continúa estrecha y deja sin uso una franja lateral sostenida.
- **Evidencia:** vídeo oficial en Partidos `01:31-02:06`, Inicio `00:17-00:19` y Telegram `03:33-03:46`; el patrón coincide con la definición estática de `.v933-two-col`.
- **Pantallas:** `/calendar`, `/app` y `/telegram`, exclusivamente en los tramos demostrados.
- **Componente:** layout compartido `.v933-two-col` y la delimitación DOM entre contenido contextual, rail y colecciones largas.
- **Impacto:** desperdicia más del 25% del viewport durante contenido abundante, reduce densidad útil y debilita la jerarquía al hacer parecer incompleto el lateral derecho.
- **Causa raíz:** la rejilla `minmax(0,1.65fr) minmax(280px,.72fr)` modela dos columnas rígidas, pero sus consumidores la utilizan también como contenedor de colecciones que deberían continuar a ancho completo tras el contexto lateral.
- **Consumidores afectados:** calendario de partidos, inicio cliente y Telegram cliente. No se autoriza extender el cambio a otras rutas sin evidencia propia.
- **Complejidad:** media; requiere delimitar el tramo de rail sin duplicar contenido ni introducir una segunda implementación del layout.
- **Riesgo:** medio; una separación incorrecta podría alterar el orden de lectura, la relación contexto/acción o el responsive. La corrección debe conservar DOM semántico, rutas, datos y apilado móvil.

**Contrato oficial de rail contextual acotado:**

- **Rail acotado:** `.v933-two-col` solo puede agrupar contenido principal y lateral cuya altura útil sea comparable; no puede encerrar una colección repetitiva que continúe más de una altura de viewport tras terminar la otra columna.
- **Continuación a ancho completo:** listas de partidos y bloques repetitivos extensos deben vivir fuera del rail y declarar `data-v939-layout-contract="full-width-continuation"`.
- **Franja contextual:** proveedor, fecha y siguiente acción pueden anteceder a una colección mediante el grid compartido y `data-v939-layout-contract="context-strip"`; no duplican ni recalculan contenido.
- **Par equilibrado:** dos bloques finales de alcance equivalente pueden reutilizar `.v933-two-col.is-balanced`; no se considera rail y ambas columnas tienen el mismo ancho.
- **Responsive:** el orden fuente prioriza la tarea principal en móvil; cualquier reordenación de contexto solo se permite en escritorio y debe conservar lectura, foco y rutas.
- **Invariante medible:** ningún consumidor puede dejar sin uso más del 25% del viewport durante más de una altura de pantalla mientras sigue existiendo contenido principal abundante.



- **Pantallas y timestamps:** Partidos 01:31-02:06; Inicio 00:17-00:19; Telegram 03:33-03:46.
- **Elemento:** layout de dos columnas.
- **Descripción:** cuando el rail termina, la columna principal sigue limitada a aproximadamente dos tercios del ancho. En la lista larga de Partidos queda una franja vacía sostenida a la derecha; también aparece desequilibrio en accesos rápidos y la parte inferior de Telegram.
- **Impacto:** reduce densidad útil y agrava el defecto de las match cards.
- **Causa raíz:** **CONFIRMADA EN CÓDIGO.** `.v933-two-col` mantiene siempre `1.65fr + minmax(280px,.72fr)` con `align-items:start`, aunque el contenido lateral sea mucho más corto.
- **Solución:** separar bloques con rail de los bloques de colección; las colecciones largas deben recuperar el ancho completo cuando termina el contexto lateral.
- **Complejidad:** media.
- **Riesgo de corregir:** medio por el uso compartido del layout.
- **Check futuro:** no debe quedar un área vacía continua superior al 25% del viewport durante más de una altura de pantalla cuando hay contenido principal abundante.
- **Aprendizaje permanente:** Visual Worker compara ocupación de columnas; AutoPilot propone cambio solo en la ruta afectada.

**Cierre local P2.1:**

- **Corrección:** Calendar separa la franja contextual de su colección y recupera el 100% del ancho; Inicio mueve “Tus accesos rápidos” fuera del rail; Telegram limita el rail a conexión/pasos y presenta confianza/calidad como par equilibrado.
- **Browser QA:** seis capturas reales locales de `/app`, `/calendar` y `/telegram` en 1366x768 y 390x844; HTTP 200, 0 overflow, 0 errores de consola, 0 errores de página, 0 peticiones externas y 0 tokens `None/null/undefined`.
- **Geometría:** 0 rails desktop con diferencia superior a una altura de viewport; todas las continuaciones ocupan el 100% del ancho de página. El aviso bruto de altura en `/app` móvil se descarta correctamente porque las columnas están apiladas, no existe área lateral vacía.
- **Comparación con vídeo:** en el estado equivalente ya no aparece la franja derecha sostenida de Partidos, los accesos de Inicio continúan a ancho completo y el final de Telegram no deja una columna vacía.
- **Sentinel:** diagnóstico estático 10.0/10, 39 rutas, 0 incidencias, 695 reglas de ruta, 944 enlaces, 0 rotos y 0 bucles; ninguna acción peligrosa ejecutada.
- **Regla permanente:** `visual_layout_occupancy` usa los marcadores `bounded-rail`, `context-strip`, `full-width-continuation` y `balanced-pair`; abre P2 cuando el vacío horizontal supera el 25% durante más de una altura de viewport.
- **Aprendizaje AutoPilot:** la incidencia debe incluir ruta, contrato y geometría; puede proponer separar el consumidor concreto, pero nunca autoaplica CSS/DOM ni extiende el cambio a otras rutas sin evidencia.
- **Check:** `tests/test_v939_product_perfection_p2.py` valida contrato, orden móvil, par equilibrado, CSS responsive y parseo Jinja. Resultado: 5/5; card canónica P1: 1/1.


#### PQV939-005 — Iconos de reglas de confianza se convierten en cajas vacías

- **Pantallas y timestamps:** Inicio 00:00-00:12; Picks 02:20-02:40; SHARK 03:00-03:13.
- **Elemento:** reglas “Picks completos”, “Histórico evaluable”, “Sin beneficio garantizado”.
- **Descripción:** el icono aparece como un rectángulo vacío antes de cada etiqueta, mientras el icono principal del mismo panel sí se renderiza correctamente.
- **Impacto:** parece un asset roto o un checkbox sin estado.
- **Causa raíz:** **CONFIRMADA EN CÓDIGO.** `.v935-customer-trust-rules span` aplica el estilo de chip también al `span` interno que contiene el icono. El selector debe dirigirse al hijo directo.
- **Solución:** limitar el selector a `.v935-customer-trust-rules > span` y mantener una regla específica para `.v933-icon`.
- **Complejidad:** baja.
- **Riesgo de corregir:** bajo.
- **Check futuro:** los tres SVG deben tener tamaño visible y ningún icono debe heredar padding/borde de su chip padre.
- **Aprendizaje permanente:** Sentinel detecta iconos con caja mayor que su SVG o sin trazo visible; AutoPilot puede sugerir el selector, no aplicarlo sin QA.

#### PQV939-006 — Lenguaje técnico interno visible al cliente

- **Pantallas y timestamps:** repetido en Inicio, Partidos, Live, Picks y SHARK; especialmente 00:00, 02:07 y 02:13.
- **Elemento:** mensajes de sincronización y contrato de Live.
- **Descripción:** aparecen textos como “actualizados desde DB/cache” y “DB y caché durante render”. Son útiles para operaciones, pero no para una experiencia cliente premium.
- **Impacto:** hace que el producto parezca un panel técnico y obliga al usuario a interpretar implementación.
- **Causa raíz:** **CONFIRMADA EN CÓDIGO.** el macro compartido de realtime consume `safe_message` técnico y `live.html` incluye literalmente “DB y caché durante render”.
- **Solución:** traducir a resultado de usuario: “Datos guardados y disponibles sin depender del proveedor en este momento”. Mantener DB/cache/render solo en admin.
- **Complejidad:** baja.
- **Riesgo de corregir:** bajo si no se elimina la transparencia sobre frescura.
- **Check futuro:** lista de términos técnicos prohibidos en templates cliente, con whitelist para nombres de fuente cuando aporten trazabilidad.
- **Aprendizaje permanente:** Sentinel clasifica copy técnico por audiencia; Company Intelligence conserva el detalle técnico en evidencia admin.

#### PQV939-007 — Fecha de sincronización en formato ISO crudo

- **Pantallas y timestamps:** barra de sincronización y paneles laterales en casi todo el recorrido, por ejemplo 00:25, 02:07 y 02:26.
- **Elemento:** `2026-07-22T14:25:21+02:00`.
- **Descripción:** la hora es correcta y trazable, pero su formato es técnico y menos legible que “22 jul 2026, 14:25 · Madrid”.
- **Impacto:** reduce claridad y coherencia con la promesa “Hora Madrid”.
- **Causa raíz:** **CONFIRMADA EN CÓDIGO.** `realtime_state_bar` y `provider_state` imprimen `last_safe_sync`/`last_sync` sin filtro de presentación.
- **Solución:** filtro único de fecha Madrid para cliente; conservar ISO en atributos o APIs admin.
- **Complejidad:** baja.
- **Riesgo de corregir:** bajo, siempre que el valor original permanezca disponible para máquinas.
- **Check futuro:** ningún timestamp ISO crudo en HTML cliente; zona Madrid explícita.
- **Aprendizaje permanente:** Sentinel inspecciona texto visible con patrón ISO; AutoPilot propone filtro compartido.

#### PQV939-008 — La lista de 108 partidos exige un recorrido excesivo

- **Pantalla y timestamps:** Partidos 01:31-02:06.
- **Elemento:** listado completo de tarjetas.
- **Descripción:** el usuario tarda aproximadamente 35 segundos de scroll rápido en cruzar la agenda. Los filtros y el contexto global quedan fuera de la vista durante la mayor parte del recorrido.
- **Impacto:** localizar un partido concreto exige demasiado esfuerzo y el usuario pierde orientación.
- **Causa raíz:** **CONFIRMADA EN CÓDIGO PARA EL RENDER.** `calendar.html` recorre todos los grupos, ligas y partidos del conjunto sin una variante compacta ni contexto persistente. La decisión de producto óptima requiere validación con uso real.
- **Solución:** primero corregir densidad y ancho; después valorar cabeceras de liga persistentes o una presentación progresiva usando controles existentes. No añadir mecanismos nuevos sin evidencia de uso.
- **Complejidad:** media.
- **Riesgo de corregir:** medio; no debe ocultar encuentros válidos.
- **Check futuro:** prueba de tiempo hasta localizar un partido por liga/equipo y límite de longitud visual por estado de filtro.
- **Aprendizaje permanente:** Company Intelligence mide uso de filtros y profundidad de scroll antes de recomendar paginación o colapso.

#### PQV939-009 — SHARK presenta su respuesta como un bloque denso y con etiqueta inglesa

- **Pantalla y timestamps:** SHARK 03:13-03:19.
- **Elemento:** “Respuesta actual / Summary” y párrafo de respuesta.
- **Descripción:** la respuesta mezcla resumen, cifras, límites, plan y riesgo en un único párrafo pequeño. La etiqueta “Summary” rompe el idioma de la interfaz.
- **Impacto:** la información más diferencial del producto se escanea peor que los módulos secundarios.
- **Causa raíz:** **CONFIRMADA EN CÓDIGO.** el motor concatena fragmentos de texto y el template imprime `answer.answer` en un solo `<p>`; `answer.focus` conserva el valor `summary` y se capitaliza sin traducción.
- **Solución:** presentar el mismo contenido en secciones breves “Situación / Evidencia / Límite / Siguiente acción” y traducir el focus. No generar información nueva.
- **Complejidad:** media.
- **Riesgo de corregir:** bajo si solo cambia presentación.
- **Check futuro:** longitud máxima por párrafo, etiqueta española y presencia de una acción visible.
- **Aprendizaje permanente:** Visual Worker detecta bloques de texto excesivos; Company Intelligence comprueba que toda afirmación numérica tenga el snapshot canónico.

#### PQV939-010 — Competición repetida dentro de cada tarjeta ya agrupada

- **Pantalla y timestamps:** Partidos 01:31-02:06.
- **Elemento:** cabecera de cada match card.
- **Descripción:** el grupo ya identifica la competición, pero cada tarjeta vuelve a mostrarla. En “Club Friendlies” y nombres largos, esa repetición consume altura y contribuye al wrapping.
- **Impacto:** baja densidad y ruido visual en el listado principal.
- **Causa raíz:** **CONFIRMADA EN CÓDIGO.** `match_card` siempre imprime competición; `calendar.html` lo invoca dentro de grupos de liga sin variante compacta.
- **Solución:** variante contextual para grupo de liga que omita el dato repetido y conserve país/hora/fuente donde aporten valor.
- **Complejidad:** baja-media.
- **Riesgo de corregir:** bajo si la competición sigue visible en el encabezado y accesible para lectores de pantalla.
- **Check futuro:** no repetir en todas las tarjetas un campo ya presente en el encabezado inmediato.
- **Aprendizaje permanente:** AutoPilot identifica duplicación contextual, pero requiere aprobación de producto antes de ocultar copy.

#### PQV939-011 — La grabación canónica contiene un identificador personal visible

- **Pantalla y timestamps:** Mi cuenta 03:46-03:50.
- **Elemento:** correo de la cuenta usada para grabar.
- **Descripción:** es correcto que el titular vea su correo en su perfil; el riesgo aparece al convertir esa grabación en artefacto compartido de referencia.
- **Impacto:** privacidad y distribución interna/externa del material de QA.
- **Causa raíz:** **CONFIRMADA EN VÍDEO.** se utilizó una cuenta con datos identificables y no se redactó la captura.
- **Solución:** conservar el original con acceso restringido y generar una copia redactada para QA, documentación o terceros. No ocultar el correo al propio usuario en producto.
- **Complejidad:** baja.
- **Riesgo de corregir:** bajo.
- **Check futuro:** guard de PII sobre capturas/vídeos antes de adjuntarlos a reportes o repositorios.
- **Aprendizaje permanente:** Company Intelligence registra solo la existencia del hallazgo, nunca el valor del identificador.

### P3

#### PQV939-012 — Flash breve de iconos fallback durante la navegación

- **Pantalla y timestamp:** entrada a Partidos, aproximadamente 00:24.8-00:25.7.
- **Elemento:** iconos de navegación y cabecera.
- **Descripción:** durante menos de un segundo algunos iconos aparecen como pequeños cuadrados antes de convertirse en SVG.
- **Impacto:** detalle de carga perceptible; no bloquea la tarea.
- **Causa raíz:** **CAUSA PROBABLE.** el HTML trae el fallback de `.v928-icon::before` y `v930-icons.js` sustituye el contenido tras `DOMContentLoaded`.
- **Solución:** evitar mostrar el fallback geométrico antes de hidratar los iconos o entregar el SVG crítico desde servidor.
- **Complejidad:** baja-media.
- **Riesgo de corregir:** bajo.
- **Check futuro:** filmstrip de primera carga sin cambio de glifo.
- **Aprendizaje permanente:** Visual Worker compara el primer frame estable con el frame tras un segundo.

#### PQV939-013 — Terminología parcialmente mezclada

- **Pantallas y timestamps:** Histórico 02:41-03:00; SHARK 03:13-03:19; Live 02:13.
- **Elemento:** “Winrate”, “Stake”, “Void”, “Summary”, “Board”.
- **Descripción:** algunos términos son habituales en el sector, pero la mezcla no sigue una regla visible. “Summary” es claramente accidental; los demás requieren decisión editorial.
- **Impacto:** reduce consistencia de marca y accesibilidad para usuarios no expertos.
- **Causa raíz:** literales de template y valores internos no normalizados por un glosario de cliente.
- **Solución:** glosario oficial: “Resumen”, “Tasa de acierto”, “Unidades”, “Nulo” y “Panel en vivo”, manteniendo ROI/SHARK/Telegram/picks solo si la marca los aprueba.
- **Complejidad:** baja.
- **Riesgo de corregir:** bajo.
- **Check futuro:** auditor de copy con whitelist de términos de marca y proveedor.
- **Aprendizaje permanente:** Sentinel marca términos internos no incluidos en el glosario.

#### PQV939-014 — Vocabulario de CTA sin una convención única

- **Pantallas:** recorrido completo.
- **Elemento:** “Ir a picks”, “Ver picks”, “Revisar picks”, “Consultar SHARK”, “Entender SHARK”.
- **Descripción:** las acciones funcionan como orientación contextual, pero verbos distintos describen destinos equivalentes sin una taxonomía clara.
- **Impacto:** microfricción y menor consistencia.
- **Causa raíz:** textos definidos por cada template sin catálogo común de comandos.
- **Solución:** convención por intención: “Ver” para navegar, “Revisar” para evaluar, “Consultar” para pedir contexto.
- **Complejidad:** baja.
- **Riesgo de corregir:** bajo.
- **Check futuro:** mismo destino + misma intención = mismo verbo.
- **Aprendizaje permanente:** Company Intelligence mantiene catálogo de CTA y señala divergencias, sin reescribir automáticamente.

#### PQV939-015 — Actividad de cuenta con metadatos redundantes

- **Pantalla y timestamps:** Mi cuenta 03:50-04:05.
- **Elemento:** filas de actividad.
- **Descripción:** cada fila repite “Actividad” y “Registrado”, mientras la información diferenciadora queda en una frase secundaria.
- **Impacto:** escaneo más lento y sensación de tabla genérica.
- **Causa raíz:** estructura de fila con categoría y estado constantes para eventos homogéneos.
- **Solución:** convertir la acción concreta en título y reservar el estado para excepciones o resultados útiles.
- **Complejidad:** baja.
- **Riesgo de corregir:** bajo.
- **Check futuro:** no repetir un metadato idéntico en todas las filas si no ayuda a comparar.
- **Aprendizaje permanente:** Visual Worker detecta columnas o badges sin variación informativa.

#### PQV939-016 — Footer público y footer autenticado no comparten la misma composición

- **Pantallas y timestamps:** páginas autenticadas en sus finales; home pública 04:18-04:20.
- **Elemento:** bloque legal.
- **Descripción:** el footer autenticado aparece centrado y contenido en un bloque estrecho; el público ocupa una banda más plana y alineada a la izquierda.
- **Impacto:** inconsistencia menor de sistema visual.
- **Causa raíz:** shells o variantes de footer distintas.
- **Solución:** conservar diferencias funcionales, pero unificar tipografía, ancho óptico, bordes y separación.
- **Complejidad:** baja.
- **Riesgo de corregir:** bajo.
- **Check futuro:** comparación visual automática de la familia legal entre shells.
- **Aprendizaje permanente:** Visual Worker agrupa componentes por función, no solo por selector.

## 7. Resumen de severidad

| Severidad | Cantidad | Estado |
|---|---:|---|
| P0 | 0 | Ninguno demostrado |
| P1 | 3 | PQV939-001 y PQV939-002 resueltos localmente; PQV939-003 abierto por cobertura |
| P2 | 8 | PQV939-004 resuelto localmente; 7 permanecen abiertos |
| P3 | 5 | Pulido y consistencia |
| **Total** | **16** | 3 resueltos localmente; 13 permanecen abiertos |

## 8. Matriz pantalla por pantalla

| Pantalla | Layout | Cards | Tipografía/copy | Navegación | Datos/estado | Resultado de vídeo |
|---|---|---|---|---|---|---|
| `/app` | Rail acotado; accesos continúan a ancho completo | Vídeo: comprimidas; post-P1: card canónica PASS | Copy clara; tecnicismo DB/cache | Clara y activa | Snapshot canónico; indicadores de confianza P2 abiertos | **MUY BUENO; PQV939-004 resuelto localmente** |
| `/calendar` | Colección a ancho completo tras franja contextual | Vídeo: wrapping crítico; post-P1: desktop/móvil PASS | Filtros claros | Exceso de scroll sigue abierto como PQV939-010 | Métricas del contrato único | **MUY BUENO; PQV939-004 resuelto, otros P2 abiertos** |
| `/live` | Estructura clara | Próximos usan card canónica | “Board” y copy técnico | CTA útiles | `live_confirmed` y `matches_today` comparten snapshot | **MEJORABLE; P1 resuelto localmente** |
| `/picks` | Buena jerarquía | Empty state correcto | Mensaje responsable | Tabs claras | No inventa pick; iconos de reglas deformados | **MUY BUENO con P2** |
| `/track-record` | Equilibrado | Estados vacíos correctos | Mezcla Winrate/Stake/Void | Clara | No fabrica ROI | **MUY BUENO** |
| `/shark` | Buena identidad | Módulos claros | Respuesta densa y “Summary” | Buenas siguientes acciones | Resumen numérico consume el contrato único | **MEJORABLE; P1 resuelto, P2 abierto** |
| `/telegram` | Rail acotado y cierre equilibrado | Beneficios claros | Copy confiable | Flujo en tres pasos | Estado real; PII de código no se replica en este informe | **MUY BUENO; PQV939-004 resuelto localmente** |
| `/profile` | Buena estructura | Servicios y plan consistentes | Actividad repetitiva | Logout visible | PII correcta para titular, sensible en vídeo | **MUY BUENO con riesgo de evidencia** |
| `/` | Hero y jerarquía fuertes | Vídeo: comprimidas; post-P1: card canónica PASS | Propuesta clara | CTA visibles | Estados y métricas del snapshot canónico | **MUY BUENO; P1 resuelto localmente** |
| Admin | No aparece | No aparece | No aparece | No aparece | No aparece | **NO CERTIFICADO** |
| Móvil | No aparece | No aparece | No aparece | Bottom nav no aparece | No aparece | **NO CERTIFICADO** |

## 9. Orden obligatorio de corrección futura

1. **PQV939-001 — RESUELTO LOCALMENTE:** contrato único de métricas deportivas.
2. **PQV939-002 — RESUELTO LOCALMENTE:** match cards y grid de colección.
3. **PQV939-003:** completar evidencia admin y móvil; no es un cambio de código.
4. **PQV939-004 — RESUELTO LOCALMENTE:** rail contextual acotado y continuidad a ancho completo.
5. **PQV939-005:** selector de iconos de confianza.
6. **PQV939-006 y PQV939-007:** copy cliente y fecha Madrid.
7. **PQV939-008 y PQV939-010:** densidad y navegación de agenda.
8. **PQV939-009:** estructura de respuesta SHARK.
9. **PQV939-011:** copia redactada del vídeo.
10. **PQV939-012 a PQV939-016:** pulido P3.

P1 funcional está cerrado. Los P2 avanzan uno por uno y cada cierre exige captura antes/después en el mismo timestamp o estado equivalente; PQV939-003 permanece como bloqueo de evidencia global, no como defecto funcional.

## 10. Reglas permanentes de calidad

| Regla | Sentinel | AutoPilot | Company Intelligence |
|---|---|---|---|
| Métricas equivalentes comparten snapshot y scope | Compara rutas/APIs y abre P1 | Propone consumidor divergente | Conserva definición, fuente, edad y evidencia |
| CTA no se parte en palabras | OCR/DOM por viewport | Crea tarea CSS | Relaciona todas las rutas del componente |
| Card respeta ancho mínimo contextual | Screenshot + bounding boxes | Sugiere variante, no la aplica | Mide recurrencia por componente |
| Rail no deja más del 25% inútil | Mapa de ocupación | Abre P2 visual | Prioriza por rutas y tiempo de exposición |
| Cliente no ve internals DB/cache/render | Linter por audiencia | Propone copy aprobado | Conserva detalle técnico solo en admin |
| Fechas cliente usan Madrid legible | Regex sobre texto visible | Propone filtro común | Conserva ISO como evidencia de máquina |
| Iconos no heredan estilos de chip padre | DOM/CSS computed style | Sugiere selector directo | Registra regresión de componente |
| No se certifica lo no capturado | Manifiesto de cobertura | Bloquea cierre automático | Usa `BLOCKED_BY_EVIDENCE` |
| Evidencia visual no contiene PII sin redactar | Guard local previo a publicación | Bloquea adjunto | No almacena el dato detectado |
| SHARK no presenta cifra fuera del contrato | Invariante de snapshot | Solicita revisión humana | Vincula respuesta a evidencia y timestamp |

## 11. Límites de esta auditoría

- No se han pulsado todos los botones; su destino no queda certificado solo por ser visible.
- El vídeo original no abre la consola; el Browser QA posterior de las tres rutas afectadas sí la monitoriza y registra 0 errores.
- No se mide rendimiento de red ni backend con el vídeo.
- No se certifican datos de producción; solo se audita lo presentado visualmente.
- No se certifica globalmente móvil, tablet, admin, formularios, modales, detalle de partido, membresías, soporte, login, registro, 404 o 500. Solo `/app`, `/calendar` y `/telegram` quedan validados en móvil para PQV939-004.
- No se declara pixel-perfect.
- No se ha usado el sitio externo mostrado al final como evidencia de NeMeSiS.

## 12. Gate de auditoría

**AUDITORÍA DEL RECORRIDO CLIENTE DESKTOP:** COMPLETA.

**AUDITORÍA DEFINITIVA DE TODA LA APLICACIÓN:** BLOQUEADA POR COBERTURA DE VÍDEO.

**CORRECCIONES APLICADAS:** 2 defectos P1 y PQV939-004 resueltos y validados localmente; los otros 7 P2 y los 5 P3 no se han modificado.

**SIGUIENTE ACCIÓN ÚNICA:** revisión humana de las seis capturas de PQV939-004; después, y solo con aprobación explícita, seleccionar PQV939-005 como siguiente P2. PQV939-003 requiere una referencia complementaria de admin y otra móvil.
