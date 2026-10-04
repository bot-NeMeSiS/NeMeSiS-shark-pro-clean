# NeMeSiS — consolidación del Core y revisión Client / Founder

Fecha: 4 de octubre de 2026, Europe/Madrid.
Rama: `redesign/core-client-founder-20261004`.
Base: `b7e8aea1`. Trabajo local, sin merge, deploy ni envío real a Telegram o Stripe.

## Qué se ha implementado

- Se mantiene el bundle canónico existente. Se modifican sus fuentes, sin agregar una hoja de overrides ni otra capa CSS.
- Se neutralizan 178 declaraciones exactamente duplicadas, conservando selectores, contextos condicionales y el último propietario en la cascada. No se elimina CSS dinámico basándose solo en pantallas vacías.
- El Core utiliza una base oscura más neutra, superficies elevadas y radio compartido de 14 px. El fondo deportivo deja de descargar la imagen oceánica que competía con el contenido.
- LIVE dispone de un tono semántico independiente, rojo. El resumen sin partidos en directo usa tono neutro, sin sugerir actividad inexistente.
- SHARK utiliza violeta en sus acciones y verde/violeta en el tratamiento de respuestas. Se conserva la identidad oficial existente.
- La navegación depende de la superficie visitada. Una cuenta admin en una página cliente no activa el shell administrativo; el chip de acceso cliente muestra ELITE en vez de ADMIN, sin modificar permisos ni membresías almacenadas.
- Los componentes de actualización filtran diagnósticos técnicos tanto en Jinja como en actualizaciones JavaScript. El modo técnico se restringe a rutas admin. Los estados desconocidos de evidencia reciben una etiqueta natural.
- La vista de revisión cliente deja de mostrar mensajes de DB, Telegram/Stripe desactivados y otros detalles operativos del entorno local.
- Login utiliza el botón canónico y una descripción orientada a empezar a seguir partidos.
- Onboarding reutiliza paneles, acciones, encabezados y estados canónicos. Su progreso usa un elemento accesible; se mantienen los enlaces y datos existentes.
- SHARK elimina referencias al modelo, al mecanismo de navegación y a la implementación del asistente; conserva límites, bloqueo de consultas y advertencia sobre resultados.
- Admin/Founder muestran al principio un aviso de bloqueo del Master Finalization Program por certificación de almacenamiento pendiente. No se modifica ni se desbloquea la lógica de certificación.

## Visual Master operativo para esta rama

| Elemento | Cliente | Founder / Admin |
|---|---|---|
| Base | Dark Premium, contenido deportivo primero | Mismo Core, densidad operativa |
| Acción | Azul; foco visible y áreas táctiles | Acciones de revisión; operaciones conservan sus protecciones |
| LIVE | Rojo, solo con estado confirmado | Estado operativo separado |
| SHARK | Violeta y verde para inteligencia | Diagnóstico y propuestas según permisos |
| Premium | PRO azul, ELITE oro | No altera acceso real |
| Escudos | Asset existente y fallback de iniciales | Mismo componente |
| Navegación | Cabecera en PC, barra inferior y cuenta en móvil | Rail y cabecera operativa; adaptación propia |
| Datos ausentes | Explicación natural; no inventar cobertura | Evidencia y bloqueos disponibles |

Las referencias históricas de `reference_images/` siguen sirviendo para estructura e identidad. La dirección de este encargo prevalece sobre su anterior regla de LIVE verde y fondo oceánico dominante. No se afirma una coincidencia exacta de píxeles con esas maquetas.

## Bloques y límites de validación

| Bloque | Cambios / revisión | Evidencia pendiente |
|---|---|---|
| A — Shell, Home, navegación | Core, fondo, aislamiento por superficie, Home sin LIVE ficticio; PC y móvil revisados | Home con agenda y favoritos reales |
| B — Live, Calendar, Match Center | Estado LIVE canónico, frontera de copy, rutas y estado de partido no disponible revisados | Partido real con marcador, eventos, estadísticas y alineaciones; no hay partidos en la DB aislada |
| C — Picks, Combinadas, SHARK | Core compartido, identidad y formulario SHARK; Picks y constructor revisados sin publicaciones inventadas | Pronósticos y cuotas publicados verificables; respuesta IA real no invocada |
| D — Cuenta, membresías, login, onboarding | Acceso y bienvenida canónicos; estados vacíos y formularios revisados | Flujos reales de compra y entrega deliberadamente no ejecutados |
| E — Admin / Founder | Separación del shell, bloqueo de almacenamiento arriba; rutas operativas y ambos Founder revisados | Certificación externa de persistencia y datos de operación reales |
| F — Móvil / rendimiento | 320, 390, 768 y 1440 px; comprobaciones de overflow, navegación y recursos | Dispositivos físicos, carga de producción y benchmark SQL antes/después |

Esta entrega no constituye una certificación completa del rediseño definitivo. Revisa el Core y las superficies disponibles; las pantallas deportivas pobladas siguen pendientes de evidencia real. No se ha hecho una reconstrucción exhaustiva de todos los selectores legacy: siguen existiendo ocho fuentes de compatibilidad y un bundle grande.

## Validación ejecutada

- 104 capturas finales y 8 adicionales de Founder, con sesión local real y aplicación Flask: PC 1440×900, tablet 768×1024, móvil 390×844 y móvil pequeño 320×740.
- 0 overflow horizontal, 0 IDs duplicados detectados, 0 errores JavaScript, 0 imágenes rotas visibles y 0 respuestas 5xx en esta matriz.
- 0 intentos de llamadas externas y 0 términos técnicos detectados por el escáner de texto visible en las superficies cliente examinadas.
- `/match/unavailable` devuelve 404 deliberadamente y muestra el estado de partido no disponible. Ese resultado no certifica un Match Center poblado.
- 197 plantillas Jinja parseadas sin errores.
- Suite final de Core, presentación, Home, hora Madrid, onboarding y acceso: 125 pruebas superadas, 0 errores y 0 fallos; resultado en `tests.xml`.
- Suite de sesiones concurrentes, membresías, límites SHARK y backups: 28 pruebas superadas; prueba de checkout local seguro: 1 superada en su entorno requerido.
- Pruebas de tarjetas Telegram: las pruebas sin entorno local se ejecutaron aparte; los dos casos de preview con sesión y navegador se repitieron usando `prepare()` en OFFLINE_SAFE y pasan. Ningún envío real.
- Bundle regenerado y comprobado contra sus fuentes. Sintaxis JavaScript y comprobación de diff verificadas.

Las primeras ejecuciones sufrieron falta de espacio en C: y pruebas invocadas sin las variables de LOCAL SAFE. No se contabilizan como resultados válidos; se liberaron solo capturas intermedias creadas por esta revisión y se repitieron las comprobaciones afectadas. Se conservaron las evidencias finales y parte de las capturas iniciales.

## Rendimiento comparado

Comparación A/B únicamente del CSS: mismas plantillas actuales, misma DB local vacía, viewport 390×844, tres muestras por ruta y variante. El CSS anterior procede de la base Git. No es un benchmark histórico de todo el servidor.

| Ruta | Mediana CSS anterior | Mediana CSS nuevo | Recursos antes / después |
|---|---:|---:|---:|
| Home | 297,6 ms | 254,1 ms | 11 / 10 |
| Calendar | 331,5 ms | 280,1 ms | 12 / 11 |
| Live | 248,8 ms | 231,7 ms | 11 / 10 |
| SHARK | 287,3 ms | 284,6 ms | 13 / 12 |
| Cuenta | 319,5 ms | 280,1 ms | 10 / 9 |

El progreso accesible se añadió después de ese A/B: incorpora 67 bytes CSS y no descarga assets. El bundle final pasa de 1.249.116 a 1.249.344 bytes (+228). La neutralización de duplicados mejora las fuentes; cssnano ya eliminaba gran parte de la redundancia del archivo servido. No se atribuye a esta limpieza una reducción inexistente del bundle.

No se introducen consultas DB ni llamadas a proveedores en los cambios de presentación. No se ha instrumentado un contador SQL antes/después: esa comprobación cuantitativa permanece pendiente. Los datos por ruta de la última matriz están en `final/observations.json` y `founder/observations.json`; las muestras A/B están en `css-comparison.json`.

## Riesgos y bloqueos que permanecen

1. Master Finalization Program: BLOQUEADO por certificación de almacenamiento pendiente. El aviso es informativo; los servicios, DB_PATH y mecanismos de cierre existentes no se cambian.
2. No hay captura deportiva verificable suministrada en este entorno. No se certifican partidos poblados, cobertura, cuotas, pronósticos, escudos oficiales remotos ni todos los estados dinámicos.
3. El bundle de 1,25 MB y los selectores históricos necesitan una consolidación adicional por familias, con datos reales y estados dinámicos antes de retirar compatibilidad.
4. La matriz visual comprueba propiedades técnicas; la aceptación estética del Visual Master sigue requiriendo revisión de las capturas. No equivale a demostrar que todas las pantallas están terminadas.
5. Rendimiento SQL, carga de producción y dispositivos físicos no medidos. Las medianas locales son orientativas.
6. No merge, deploy, pagos, Telegram real, cambios de secretos ni certificación de almacenamiento realizados. La rama queda local y revisable.
