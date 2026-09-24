# V941 · Matriz de paridad Admin PC y móvil

Resultado: **38 casos Chromium aprobados** (14 Admin y 24 preview real), más **12 comprobaciones HTTP de enlaces de preview**. Las 14 pruebas del centro usan evidencia sintética rotulada y transporte API interceptado. Las 24 previews usan respuestas reales de Flask contra una base local aislada. Ninguna consulta producción.

## Superficie compartida

PC y móvil acceden a `/admin/dashboard` y `/admin/control-center` con las mismas rutas protegidas, catálogo de acciones y permisos. La composición de escritorio usa espacio adicional para hechos, SHARK, recomendaciones y herramientas. En móvil se reorganiza la misma vista; una acción de riesgo no pierde la confirmación al reducir la pantalla.

| Capacidad | Control compartido | Comprobación requerida |
| --- | --- | --- |
| Estado operativo | Hechos con origen y fecha; desconocido cuando no hay evidencia | PC y móvil muestran los mismos valores y estados |
| Consulta SHARK | Formulario y conversación | Teclado, envío, estado pendiente, error legible |
| Propuesta | Antes/después y diálogo de aprobación | No ejecutar al consultar; confirmar por separado |
| Ajustes | Formulario operativo | Persistencia y auditoría; conflictos de revisión y reversión |
| Herramientas | Destinos Admin existentes | Sin enlaces vacíos; rutas protegidas y navegables |
| Incidencias/mejoras | Sentinel existente | Evidencia y prompt; sin cierre falso |
| Preview | Plan FREE / PRO / ELITE y dimensión | Sesión Admin intacta; lectura sin pagos ni cambios de cuenta |
| Acciones peligrosas | Guardas en servidor | No se saltan desde móvil ni por llamada directa |
| Búsqueda de comandos | Ctrl/Cmd+K en PC y acceso visible | Navegación por teclado y cierre del diálogo |
| Historial | Auditoría de propuestas/resultados | El resultado pendiente o fallido no aparece como éxito |

## Dimensiones de revisión

Se ejecutaron 320×844, 390×844, 768×1024, 1024×768, 1366×768, 1440×900 y 1920×1080. Los siete tamaños pasaron ausencia de desbordamiento horizontal del documento, formulario visible, estados desconocidos honestos y ausencia de errores JavaScript y peticiones externas. Las tablas y el marco de preview conservan su desplazamiento interno.

La preview responsiva dentro de un iframe no certifica Safari, dispositivos físicos ni una cuenta real de cada plan. Las capturas sintéticas deben estar rotuladas como QA y usar datos aislados.

## Evidencia y resultados

Las 14 pruebas cubren siete tamaños, chat con propuesta sin ejecución automática, aprobación separada en móvil y PC, ajustes, búsqueda Ctrl+K, cierre Escape, selectores de preview, respuesta HTTP 409 sin reintento, respuesta no confiable mostrada como texto y resultado fallido que no se presenta como éxito verificado. Se encontró y corrigió un fallo: Escape sobre la búsqueda dejaba abierto el diálogo; la nueva ejecución confirma su cierre en 390 y 1440 px.

Capturas: `data/local_dev/admin-master-v941-qa/admin-320x844.png`, `admin-390x844.png`, `admin-768x1024.png`, `admin-1024x768.png`, `admin-1366x768.png`, `admin-1440x900.png` y `admin-1920x1080.png`. Se inspeccionaron visualmente las capturas de 390 y 1440 px. Evidencia de ejecución: `data/local_dev/candidate-3b29a5380a1346ec959a8236b5adc51f/result.xml`; la barrera registró `BOUNDARY_EVENTS []`.

Entorno: Python 3.12.14, pytest 8.3.4, Chromium 149.0.7827.55 con binario local existente. El pin de producción es Python 3.11.9 y no se ha certificado ese runtime. Las capturas conservan el HTML y CSS de la shell real; se excluyeron scripts compartidos de polling/PWA ajenos al cambio. El iframe de esta suite es un marco QA inerte: verifica dimensión/plan/enlace/sandbox, no el contenido real de todas las pantallas cliente. Se añadió otra matriz independiente de 24 capturas de la ruta Flask protegida real: SHARK, Telegram, Perfil y Membresías × FREE, PRO y ELITE × 390 y 1440 px. Todas pasaron CSP sin scripts, no-store, sesión Admin conservada, controles operativos inhabilitados, sin desbordamiento del documento ni errores JavaScript ni peticiones externas. Se inspeccionaron visualmente Perfil FREE 390 y SHARK PRO 1440. Las 12 comprobaciones adicionales demostraron que todos los enlaces permanecen dentro de preview y conservan el plan simulado. No se accedió a producción, envió Telegram ni ejecutó pagos reales.

Validación complementaria realizada: gate estático V941 8/8, parseo completo de 214 plantillas Jinja, py_compile de app.py y compileall de 1024 archivos Python (app, blueprints, engines, services, automation_workforce, tools, localization y tests). Siete conversiones Madrid verificaron invierno, verano, cambios DST y hora manual sin doble desplazamiento; no se reescribió ningún informe V725 histórico.

La validación estática de plantillas, versiones y enlaces no sustituye la interacción real con un navegador.





Evidencia adicional: `data/local_dev/candidate-b6df8cebce124b14b9b7ef834aae3815/result.xml` (24 previews) y `data/local_dev/candidate-a621caa622174afaafc2131da512084b/result.xml` (12 enlaces + 2 regresiones repetidas tras incorporar cancelación auditada). Capturas: `data/local_dev/admin-master-v941-qa/preview-{shark,telegram,profile,memberships}-{free,pro,elite}-{390,1440}.png`. Ambas ejecuciones registraron `BOUNDARY_EVENTS []`. Se volvieron a compilar los 10 fuentes Python modificados tras congelar la implementación; no hubo errores.
