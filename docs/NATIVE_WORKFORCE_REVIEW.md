# Revisiones nativas de plataforma y Game UI

## Objetivo y alcance

Company OS describía 15 responsabilidades y el laboratorio Game UI añadía siete
disciplinas. Esos catálogos no ejecutaban revisiones. Este cambio conecta
comprobaciones deterministas de las 22 áreas al sistema **Continuous Evolution**
que ya existe en NeMeSiS. No crea otro servicio, otro Cron ni otro panel.

La revisión consulta únicamente una lista explícita de archivos locales de código
y contratos. No requiere una conversación abierta, un modelo generativo ni
créditos de ChatGPT. Sigue necesitando que la aplicación, su almacenamiento y su
programador estén disponibles. El código preparado no acredita que la versión
desplegada ya lo ejecute.

## Ejecución y cadencias

El Cron maestro conserva la llamada protegida a
`POST /api/automation/continuous-evolution/tick`. El endpoint valida la cabecera
de automatización, el modo seguro y el almacenamiento persistente antes de
trabajar. No acepta forzar la ejecución o elegir otra tarea mediante el cuerpo
o la URL de la petición.

| Paso | Cadencia | Trabajo |
| --- | --- | --- |
| Cron maestro existente | La declarada actualmente en `render.yaml`: cada cinco minutos | Solicita el tick protegido; no necesita otro servicio. |
| `platform_workforce_review` | Una tentativa por franja horaria UTC | Ejecuta las 15 comprobaciones de plataforma y las siete disciplinas Game UI. |
| `daily_product_review` | Conserva las 04:00 de Europe/Madrid | Revisión diaria existente; incorpora propuestas del recibo nativo reciente. |
| Founder Brief | Conserva su asociación al ciclo diario | Resume el resultado y mantiene la revisión humana existente. |

Las franjas UTC permiten distinguir las dos horas locales repetidas en el cambio
de hora. Una tentativa nativa incompleta consume su franja: no se repite cada
cinco minutos. La siguiente franja puede volver a intentarlo. La pausa
administrativa existente detiene las tareas programadas.

El tick nativo se realiza antes del diario para que este pueda incorporar sus
propuestas sin repetir las comprobaciones. Un fallo nativo no queda oculto tras
un resultado diario `SKIPPED_NOT_DUE`.

## Qué aporta cada revisión

Las 15 responsabilidades comprueban contratos concretos: catálogo y separación
del inventario, sintaxis de las fuentes seleccionadas, referencias de planes,
contrato de peticiones SHARK, JSON finito, estados y límite declarado de la cola,
estados de evidencia y de grading, metadatos de identidad, esquemas de enlaces,
codificación visible, contrato de pantallas y coherencia declarada del arranque.
Ninguna de estas comprobaciones ejecuta una entrega, una apuesta, un pago o una
sesión real de usuario.

| Disciplina Game UI | Comprobación local y propuesta |
| --- | --- |
| Lectura arcade | Contratos de las pantallas deportivas; propone comprobar equipos, marcador, estado y hora en una muestra renderizada. |
| Estrategia y simulación | Acciones declaradas; propone comprobar filtros, apertura de partido y navegación de vuelta. |
| Arte técnico | Huella de las fuentes y cabecera del bundle; propone medir la visibilidad efectiva del tiburón y la oclusión por paneles. |
| Motion | Vinculación declarada del control, pausa y preferencias; propone ejecutar los escenarios de interacción existentes. |
| Accesibilidad | Preferencias declaradas de contraste y transparencia; propone medir foco, contraste y objetivos táctiles por tamaño y rol. |
| Rendimiento visual | Presupuesto declarado de assets; propone contrastarlo con transferencia y tiempos observados. |
| Dirección de QA visual | Separación entre funcionamiento, aprobación de diseño y publicación; propone vincular capturas y resultados a la revisión exacta. |

Una fuente presente no demuestra que un flujo funcione. Una imagen cargada o una
opacidad válida no demuestran que el tiburón sea visible. El análisis local no
promueve diccionarios arbitrarios de evidencia a resultados de navegador.

## Recibos y memoria

`result=PASS` en el scheduler significa **evaluación terminada**, no producto
certificado. El recibo incluye un `outcome` independiente y cada fila conserva
sus comprobaciones, resultado, alcance y límites. `executed=false` identifica
las filas que no pudieron evaluarse dentro del presupuesto.

El recibo registra identidad de ejecución, fechas, duración, archivos observados,
hashes, cobertura y propuestas. El SHA anunciado por el entorno se identifica
como anunciado y no como verificado. Si cambia entre el recibo y la lectura,
el panel trata la evidencia anterior como obsoleta. Las fechas futuras fuera
de una tolerancia de dos segundos quedan sin verificar.

Se utiliza el almacenamiento existente de Continuous Evolution. Bajo su raíz,
`native_workforce/state.json` conserva el último recibo, hasta 48 recibos de
historial y propuestas con IDs estables. Reobservar el mismo problema actualiza
la misma entrada. `UNKNOWN`, un recibo antiguo o una falta de cobertura no
resuelven ni reabren por sí solos una decisión cerrada. Un fallo estático
comprobado puede registrar una regresión.

La tarea horaria no modifica `product_memory.json`. La revisión diaria incorpora
sus propuestas al board existente y conserva el alcance nativo en esa memoria.
Las revisiones nativas tienen contadores separados de los ciclos completos.

## Límites de recursos y concurrencia

- Presupuesto cooperativo de dos segundos por pasada, ocho MiB de fuentes en
  total y tres MiB como máximo por archivo en el lector común.
- La lectura o el parseo de un archivo ya empezado no se interrumpen a mitad;
  los controles que no alcancen a ejecutarse quedan sin acreditar.
- Máximo de cuatro MiB para el estado persistido, calculado con la misma
  serialización que escribe el archivo.
- Un solo propietario del bloqueo. El estado y el vencimiento se vuelven a leer
  después de adquirirlo; otro solicitante no sobrescribe estado ni logs.
- Escritura mediante un temporal propio y sustitución atómica. Un archivo de
  memoria ilegible no se reemplaza silenciosamente por memoria vacía.
- Un bloqueo antiguo o no verificable se comunica como `STALE_LOCK` o
  `LOCK_UNVERIFIED`. No se borra automáticamente un bloqueo cuyo propietario no
  se ha verificado; requiere inspección antes de recuperar la ejecución.

La nueva pasada no consulta proveedores, ejecuta navegador, modifica datos de
negocio, cambia código, envía mensajes ni despliega. Tampoco instala un modelo
local. Las propuestas se preparan para el circuito de revisión y ejecución
existente.

## Cambio visible en Company OS

Antes: 15 tarjetas de responsabilidades y siete especialidades declaradas.
Después: las mismas tarjetas y desplegables pueden mostrar la última revisión
estática reciente, sus resultados concretos, evidencia y propuesta. Se conservan
las 15 tarjetas del inventario; las siete disciplinas usan su propia clase.

Abrir el panel solo lee recibos: no inicia trabajo ni renueva fechas. Sin recibo,
con evidencia antigua o con filas no ejecutadas, conserva el estado sin ejecución
acreditada. El enlace de mejora continua conduce al Founder Dashboard existente.
No se añaden pantallas ni se altera la identidad gráfica aprobada.

## Validación y estado de entrega

La comprobación local de las 26 fuentes permitidas de main
`33d1b85125a887bb47c036844e0f70eb474afc28`, con las fuentes modificadas del
candidato superpuestas, completó 22 evaluaciones en 1,253 segundos y leyó
4.725.149 bytes. El pase terminó con `PASS` y su `outcome` permaneció `UNKNOWN`:
no hubo pruebas de negocio, navegador ni producción. Una prueba de 51
actualizaciones conservó 48 recibos en un estado de 2.050.620 bytes.

Las regresiones cubren cadencia, concurrencia, cambios de hora, presupuesto,
pausa, aislamiento de memoria, deduplicación, corrupción, vigencia, cambio de
SHA anunciado, contratos estáticos, proyección y resumen del Cron. El entorno
local no dispone de Flask, pytest, Jinja o un navegador; los harness locales
ejecutaron los cuerpos exactos de las funciones mediante AST y el módulo Game UI
real, con I/O temporal. Esas pruebas no sustituyen la integración en CI.

Los tests HTTP de cadencia usan un presupuesto de prueba mayor para aislar sus
aserciones de la carga de CPU de CI. Las pruebas específicas de agotamiento
controlan el reloj; el presupuesto del código productivo sigue en dos segundos.
Las capturas y el resultado de CI de la revisión publicada deben evaluarse antes
de integrar el cambio. Este documento no certifica un despliegue.

## Activación y reversión

La activación utiliza el despliegue aprobado de la aplicación en el servicio
existente. Se deben comprobar allí la revisión desplegada, el Cron, el modo
seguro, la raíz persistente y el primer recibo nativo; después, la repetición de
la misma franja debe omitir trabajo y una franja posterior debe generar otro
recibo. La configuración versionada no demuestra por sí sola la configuración
real del servicio.

La pausa existente detiene nuevas ejecuciones programadas. Revertir el cambio
restaura el comportamiento previo del endpoint y Company OS; la memoria propia
permanece en disco para inspección. No se necesita borrar datos de negocio,
cambiar secretos, contratar infraestructura ni crear otro Cron.
