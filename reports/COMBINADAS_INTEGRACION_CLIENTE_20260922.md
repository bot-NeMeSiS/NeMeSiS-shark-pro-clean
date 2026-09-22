# Combinadas: integración cliente y reparación de accesos

## Punto de partida y alcance

Main verificado: `46683cd98498b3a37f27f24d829924ad41d596e0` (PR67). Se amplía la PR66 existente (`61e3c61d9837674af36e5867f603a1fd96765813`) en vez de abrir otro constructor. El árbol propuesto reconcilia la caché decorativa publicada con la revisión privada de borradores y estos ajustes. No cambia app.py, reglas de precio/estado, planes, trabajos del proveedor, pagos, Telegram, DB_PATH o secretos. No hay migraciones adicionales por esta ampliación.

La pantalla publicada ya es `templates/combis.html`, compartida por `/combis` y `/combinadas`. Ambos accesos usan el mismo manejador y la misma sesión. No existe una segunda aplicación o un segundo almacén de combinadas creado por este ajuste.

## Integración visible

- Navegación secundaria compartida: Picks / Combinadas / Mis borradores, también sin selecciones elegibles. El enlace redundante de la cabecera de Picks se sustituye por esta navegación; no se apilan dos acciones idénticas.
- La barra móvil conserva sus cinco destinos. En Combinadas permanece activa la sección Picks. Escritorio conserva sus destinos principales y la misma orientación. `aria-current=true` identifica la sección y `aria-current=page` la página en su conjunto de enlaces; no se implementa un tablist de JavaScript.
- Inicio cliente conserva sin cambios sus tres accesos rápidos: Favoritos, Membresías y Soporte. El acceso directo a Combinadas está en la cabecera del bloque de Picks, incluso cuando no hay una selección destacada. No se retira el acceso existente al plan.
- Cuenta incorpora Mis combinadas, dirigido a los borradores privados, y el mapa de funciones ofrece acceso directo al constructor.
- Las tres opciones secundarias tienen un mínimo de 44 px de alto y se pueden redistribuir sin desbordamiento de página. Se reutiliza la hoja pequeña existente de combinadas con versión de recurso actualizada en ambas pantallas.

## Fallos de entrada corregidos

Antes, un enlace con match_id marcaba todas las selecciones elegibles del mismo partido, incluidas alternativas incompatibles. Ahora, si hay una sola opción se marca y se explica que no se ha guardado; si hay varias, se muestran primero pero no se elige por el usuario.

Un pick explícito prevalece sobre un parámetro de partido adicional. Un pick ausente, inaccesible o demasiado largo no se sustituye por otra selección ni se trunca hasta coincidir con un ID distinto. El aviso no revela datos premium.

Se conservan las reparaciones previas de PR66: importe y casillas tras un error, comparación con cuotas actuales, propietario, permisos y original intacto. Las opciones dirigidas por el enlace o ya elegidas se sitúan primero. Si quedan selecciones elegidas dentro del grupo desplegable, este se abre, sin desmarcarlas ni descartar opciones.

Nada de esto coloca apuestas, guarda automáticamente, consulta cuotas al proveedor, liquida resultados, calcula una nueva probabilidad o envía avisos. El servidor sigue revalidando cada guardado mediante el contrato de PR65.

## Validación local verificable

Selección final: **234 casos distintos aprobados**, cero fallos, errores u omisiones. Incluye **28 nuevos**: entradas ambiguas, prioridad de identificadores, no sustitución, privacidad, visibilidad, barras públicas/cliente, rutas Flask reales y cuatro casos Chromium de la estructura cliente a 320/390/430/1366 px. Las pruebas anteriores de construcción, revisión privada y caché decorativa se mantienen sin relajar sus criterios.

Control anterior sobre la copia de PR66: nueve regresiones fallan y una pasa en la selección dirigida; se conservan log y XML. No se interpreta esta reproducción sintética como un incidente observado en cuentas de producción.

Compilación Python y 208 plantillas Jinja: aprobado. Comprobación de hora Madrid: aprobada. Escáner existente: 1223 archivos, cero hallazgos de secretos; conserva dos avisos de privacidad en fixtures anteriores no modificados. No se cambian filtros del escáner.

El test de rutas usa una cuenta temporal en SQLite y la retira al finalizar. Las capturas parten del HTML renderizado por Flask y sus hojas CSS reales, con red externa bloqueada y scripts retirados para comprobar la navegación convencional. Son evidencia de presentación/teclado sin red, no una visita HTTP integral en Safari, una medición de producción o una prueba de cuotas reales. No se añade BeautifulSoup ni otra dependencia al repositorio: el análisis HTML de tests usa la biblioteca estándar.

## Integración y continuidad

Los 28 casos nuevos están incluidos en los 234; no sumar pases repetidos. Los controles remotos del HEAD ampliado deben completarse antes de aceptar esta versión. Los aprobados anteriores de PR66 no se trasladan automáticamente al código nuevo. Verificar que la composición conserva la caché de PR67 y no interrumpir su observación de producción con una publicación prematura.

La PR66 y esta ampliación quedan en revisión, no declaradas desplegadas en este documento. Estadísticas permanentes, cobertura de proveedores, vídeos (PR60), inteligencia (PR59) y concurrencia (PR64) conservan sus pendientes. Este cambio no los integra ni los sobrescribe.

## Corrección posterior al primer CI del HEAD ampliado

El Smoke remoto 35705386146 falló en `test_quick_actions_remain_unique_with_same_destinations` (2014 aprobados y 1 fallo en su suite principal); los grupos posteriores no se ejecutaron. La prueba detectó que se había sustituido el atajo de Membresías por Combinadas. El registro original permanece disponible en el job 106672925006.

Se restauran los tres destinos de Inicio y se coloca Combinadas en la cabecera del bloque Pick destacado, reutilizando su acción existente. La prueba heredada se conserva intacta. La nueva regresión comprueba simultáneamente ambos hechos: los tres accesos previos permanecen y el bloque de Picks ofrece Combinadas. La selección local final incorpora las 30 comprobaciones heredadas de R8: 234 aprobadas, sin fallos ni omisiones. Se requiere un nuevo CI completo de la revisión corregida; no se reutiliza el aprobado de QA/Preflight del HEAD anterior.
