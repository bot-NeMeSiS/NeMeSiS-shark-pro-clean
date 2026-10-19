# V942 — Resúmenes, estado de pago y Sentinel

Preparación iniciada el 18 de octubre de 2026; reconciliación con el main vigente el 19 de octubre de 2026 (Europe/Madrid).

## Identidad y alcance

- Runtime candidato: `V942_HIGHLIGHTS_READ_PATH_PAYMENT_STATUS_SENTINEL`.
- Base actual comprobada de GitHub: `8ad39ea6c3b653eecbf20b15f8175313ea639118` (V941).
- Base del diagnóstico y primera regresión: `dd9a080b8e63351c1457372e9df2966e2f58e6e6`; el candidato se ha rebasado conservando las 29 integraciones posteriores.
- Rama de trabajo: `release/v942-operational-quality`.
- Estado: implementación candidata; no acredita despliegue ni funcionamiento productivo del nuevo runtime.

## Cambios

### Lectura de Resúmenes

En la base del diagnóstico, las colecciones públicas de Resúmenes cargaban `dashboard_data`, que prepara también partidos, pronósticos, combinadas y otros contextos deportivos ajenos al catálogo. HTML y API duplicaban además la lectura del resumen de medios. Se reprodujo el intento de inicialización en una petición fría.

El main posterior ya había aligerado el catálogo HTML y desactivado el recorrido de pendientes en esa página. V942 conserva ese cambio y extiende la corrección a las APIs y a la protección de inicio: catálogo y APIs construyen un contexto específico, reutilizan una sola lectura del resumen y comparten con el detalle de medios la protección de lectura que evita inicializar o crear la base de datos. Se conserva la revisión de derechos, la pausa administrativa y la distinción entre catálogo vacío y disponibilidad no comprobada. También se propaga el recuento persistido de registros asociados, antes omitido.

La prueba demuestra la eliminación del trabajo innecesario. No demuestra que fuera la única causa de los timeouts observados en producción: falta medir la latencia después de desplegar el commit aprobado.

### Estado de pago visible

La página de membresías distingue la configuración local necesaria para Checkout de la existencia de una sesión. Un visitante con configuración disponible recibe un enlace para iniciar sesión, sin recibir el aviso incorrecto de configuración pendiente.

El entorno se deduce únicamente del prefijo de la clave configurada, incluidas claves restringidas, sin exponer su valor ni llamar a Stripe. La pantalla avisa expresamente del modo de pruebas. El modo real describe el entorno; no certifica webhooks, permisos remotos, cobros ni ingresos. Un estado no legible se presenta como no disponible. Si la configuración necesaria está incompleta o los pagos están desactivados, no se presenta una acción de compra habilitada.

Se conservan los controles de usuario, plan actual, CSRF y consentimiento legal. No se ejecutan Checkout, cambios de suscripción, migraciones ni webhooks como parte de esta entrega.

### Sentinel y recursos externos

El runner reconoce el componente deportivo del DOM, en vez de deducir su función solamente de la URL. Un recurso externo con HTTP 404/410 solo queda tratado como degradación controlada cuando la respuesta GET de imagen y la alternativa visible coinciden en URL, página y navegación exacta; la imagen fallida debe estar oculta y la alternativa debe pertenecer al mismo componente y caber en él.

La carencia sigue registrada con su estado HTTP, URL, evidencia y gravedad `WARNING`, junto con `external_image_degradation_count`. Recursos locales obligatorios, marca, iconos, errores JavaScript, fallos genéricos y alternativas sin evidencia siguen sin aprobarse. Se conservan los controles de publicación y rollback. El informe antiguo de producción no se convierte retroactivamente en aprobado.

### Compatibilidad con las últimas integraciones

Los controles de main detectaron tres fixtures administrativas que seguían confiando en cookies de rol sin un usuario persistido. El gate V915 y esas pruebas ahora crean cuentas en una SQLite temporal y establecen la sesión con los helpers actuales, incluida `auth_version`. Se conservan las denegaciones anónimas y los controles CSRF; no se modifica la autorización de producción.

También se mantiene el contrato de bandas de competición apiladas en Inicio de escritorio y se corrige el espacio del reloj en las tarjetas de calendario de 320 px, conservando el tamaño de los controles táctiles. La prueba de Directo comprueba el enlace CSS canónico vigente, en lugar de exigir un sufijo histórico.

El ZIP conserva explícitamente los dos informes V941 exigidos por los contratos de empaquetado, sin ampliar los filtros generales de históricos, secretos o archivos regenerables.

## Validación local

Entorno aislado: Python 3.12, dependencias fijadas por el repositorio, Playwright 1.56.0 y Chromium 141.0.7390.37 instalados únicamente en el entorno temporal. Las dependencias versionadas del proyecto permanecen intactas. Usuarios, claves, precios, bases de datos y respuestas HTTP de las pruebas son sintéticos.

| Conjunto | Resultado |
|---|---|
| Resúmenes sobre la base actual: colección fría, detalle, derechos, configuración y consumidores | 199 aprobadas; roles PRO/ADMIN validados contra usuarios persistidos |
| Sentinel: clasificador, contratos y navegador | 137 aprobadas, incluidas 18 con Chromium real |
| Estado de membresías, pagos de solo lectura, lenguaje, identidad, webhooks y autoridad de sesión sobre la base actual | 107 aprobadas |
| Fixtures administrativas y controles de acceso | 74 aprobadas; gate V915 aprobado |
| Contratos de empaquetado tras corregir los dos informes excluidos | 60 aprobadas |
| Calendario móvil, bandas de Inicio y HTTP de Directo sobre la base actual | 60 aprobadas; aserciones de calendario e Inicio intactas |
| Análisis sintáctico e identidad de las tres autoridades | Aprobado |
| Diff con finales de línea CRLF preservados | Aprobado (`core.whitespace=cr-at-eol`) |
| Clasificación de privacidad y secretos | Aprobado: 0 secretos confirmados, 0 secretos pendientes y 0 incidencias de privacidad pendientes |
| Suite estándar completa sobre la base inicial | 5.084 aprobadas y 2 fallos de empaquetado; ambos corregidos y cubiertos por las 60 pruebas posteriores |
| CI de la propuesta sobre la base actual | Consultar los checks del head exacto de la PR; las ejecuciones anteriores no certifican este head |

Las selecciones se indican por separado; no representan mediciones de producción ni deben sumarse con futuras ejecuciones completas como si fueran pruebas distintas.

## Integración y límites

`preflight`, `qa` y `smoke` deben aprobarse en el head exacto de la propuesta antes de integrar. Web y Cron de Render siguen configurados sobre `main` con despliegue automático al recibir un commit. Esta preparación no modifica Render ni activa pagos, APIs deportivas, envíos de Telegram o generación de pronósticos.

El main actual ya incluye cambios de preparación de pronósticos y previsiones derivadas del mercado, aunque la PR #243 permanezca abierta. V942 conserva el código vigente y no integra esa PR por separado ni afirma resolver por sí sola la generación de picks o la disponibilidad de cuotas.

Tras una integración autorizada: comprobar SHA y versión en Web/Cron, medir los tiempos de Resúmenes y ejecutar Sentinel sobre ese mismo commit. La referencia de base para evaluar una reversión es `8ad39ea`; cualquier reversión debe considerar las integraciones posteriores que existan entonces.
