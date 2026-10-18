# Revisión general de NeMeSiS SHARK PRO — 18 octubre 2026

## Alcance y conclusión ejecutiva

Revisión local de producto, código, pruebas y organización Git, junto con lectura de solo lectura de Render. Corte operativo: 18 octubre 2026, 20:30 Madrid. No se inspeccionaron valores de secretos, no se hicieron llamadas a proveedores deportivos, pagos o Telegram, no se usaron datos reales en pruebas, y no se cambió GitHub ni Render.

La aplicación ya reúne una cantidad amplia de funciones: calendario, directo, estadísticas, favoritos, pronósticos, combinadas, membresías, resúmenes, medios, SHARK AI, Telegram, Stripe y herramientas administrativas. La principal oportunidad ahora no es añadir pantallas por añadir: es demostrar qué datos están frescos, conectar cada permiso a una operación real, proteger las rutas de administración, y cerrar el recorrido del cliente con información verificable.

Se preparó un primer lote local con una mejora de seguridad en cuatro límites de entrada y una compactación de la agenda de Inicio en escritorio. El lote pasó pruebas enfocadas de servidor y navegador en modo sintético. No está integrado en `main` ni desplegado.

## Identidad del proyecto y producción

| Comprobación | Evidencia del 18 oct 2026 | Lectura |
|---|---|---|
| Checkout | Rama `main`, HEAD `8babc3447a6bc9e26d112bad070bffb2582a72c1` | Es la línea local de trabajo abierta. |
| `origin/main` | Mismo SHA; diferencia 0/0 | El checkout empieza sincronizado con GitHub. |
| Render web | `srv-d7t9j2favr4c738hm0i0`, repo oficial `bot-NeMeSiS/NeMeSiS-shark-pro-clean`, rama `main`; deploy `dep-dbago95g1s2s73bb1i0g` LIVE a las 20:14 Madrid, SHA igual a HEAD; confirmado de nuevo 20:36 | Producción apunta al mismo código base al comenzar este trabajo. |
| Render Cron | `crn-d8mlmhq8qa3s73e9v2tg`, mismo repo y rama; deploy `dep-dbago9dg1s2s73bb1jmg` LIVE a las 20:13 Madrid, mismo SHA; cadencia `*/5 * * * *` | Es el único Cron listado para el proyecto. Su último éxito general no prueba por sí solo cada lane o proveedor. |
| Persistencia | Disco Render `dsk-d7t9j2favr4c738hm0q0`, montado en `/data`, 2 GB; una instancia web | Configuración confirmada; esta revisión no leyó el contenido del disco ni cambió su tamaño. |
| Salud y tráfico | GET a `/api/health` respondió HTTP 200 a las 20:37 Madrid: `ok=true`, `initialized=true`, versión V941. Métricas Render de 14:30–20:30 Madrid: máximo de memoria aproximado 259 MB sobre 537 MB entre varias instancias; un 502 a las 14:55 y un 499 a las 20:15 (este último cerca del despliegue 20:14). La consulta de logs de petición no devolvió entradas coincidentes. | La ruta de salud y Render están activos en ese instante. Los 502/499 requieren observación, sin evidencia suficiente para atribuir causa ni declarar un fallo persistente. Health 200 y memoria acotada no certifican estabilidad general. |

La respuesta de salud confirma que la aplicación atiende en la versión V941, pero no devuelve el SHA ni certifica la frescura de partidos, proveedores, permisos, pagos, backup o ejecución de cada lane del Cron.

## Tamaño y organización del código

- `app.py` tiene aproximadamente 33.300 líneas y cerca de 808 rutas declaradas. El backend principal es Flask con SQLite.
- El checkout contiene 1.306 archivos Python rastreados, 203 plantillas y 319 archivos de pruebas rastreados. Los módulos de `engines/` cubren deportes, directo, estadísticas, pronósticos, apuestas, vídeo, membresías, Telegram, Stripe y automatización.
- Hay 189 referencias de ramas y 47 worktrees locales. No se eliminaron, archivaron, cambiaron de rama ni fusionaron. El recuento por sí solo no identifica qué trabajo es basura: antes de limpiar, comparar cada diferencia con `main` y proteger cambios sin commit.
- Ejemplos de ramas que necesitan revisión individual, no integración automática: `codex/full-platform-consolidation-20261017` (18 commits por delante/27 detrás de `main` en las referencias locales observadas), `codex/past-match-highlights` (3/31), `codex/client-sports-reliability-20261017` (4/27), `codex/control-center-reliability-20261017` (1/27), `codex/highlights-admin-readiness-20261018` (2/24). Pueden contener cambios útiles, pero están basadas en versiones anteriores y pueden solaparse.
- `reports/` contiene 1.775 archivos. Es valioso como historial, pero difícil de navegar. Conviene conservar la evidencia y crear un índice corto por tema y fecha antes de plantear cualquier archivo.
- `README_MASTER.md` todavía llama “actual” a V600/V601 mientras `app.py` declara V941; `NEMESIS_LIVING_ROADMAP.md` mantiene un bloqueo LRM-001 fechado en julio. Son documentos históricos desalineados, no prueba de que el runtime esté detenido.

## Capacidades encontradas y límites de lo demostrado

| Área | Código presente | Lo que aún hay que probar para llamarlo listo para clientes |
|---|---|---|
| Fútbol | Calendario, equipos, competiciones, directo, eventos, estadísticas y capas de presentación | Frescura y disponibilidad por partido; mostrar cuándo un dato falta o está desactualizado; no todos los encuentros incluyen todas las estadísticas. |
| Pronósticos y combinadas | Motores de cuotas, pronóstico, selección, seguimiento y evaluación histórica; tablas `market_forecast_snapshots`, `historical_recommendations` y `combis` | Cada recomendación visible debe enlazar fuente, hora, mercado, estado y resultado; separar dato del proveedor, caché y análisis interno; mostrar rendimiento medido con muestra y metodología, sin promesas. |
| Resúmenes y vídeo | Catálogo, asociación, política de contenido, revisión y superficies | Cobertura real por partido, URL reproducible y derechos. `RIGHTS_REVIEW` no autoriza publicar; una ficha existente no prueba que el vídeo esté disponible. |
| Proveedores | Adaptadores para API-Football/API-Sports, The Odds API, TheSportsDB, Telegram y Stripe | Presencia de código o clave no prueba plan, autenticación, permiso de endpoint, cuota disponible o entrega efectiva. El Centro de Mando debe distinguir configuración, plan verificado, última llamada externa, caché, resultado y hora. |
| Administración | Paneles de operaciones, automatización, miembros, métricas y proveedores | Que cada botón tenga una acción real, autorización de servidor, resultado visible, registro de auditoría y recorrido responsive equivalente. |
| Empleados | La autorización principal de usuarios valida `FREE`, `PRO`, `ELITE` y `ADMIN` (`app.py:11468`) | Los roles `SUPPORT`, `OPERATIONS`, `CONTENT/MARKETING`, `TECHNICAL`, finanzas de solo lectura y el control exclusivo de OWNER todavía no existen en el esquema principal de roles. No confundir roles de herramientas internas de crecimiento con permisos de la aplicación. |

### Proveedores: evidencia disponible y fecha

El informe `reports/API_INTEGRATIONS_USAGE_AUDIT_20261017_1848.md` contiene la última verificación de cuenta accesible antes de esta revisión. Sus datos son del 17 de octubre, no una prueba de estado actual al 18:

- API-Football Pro aparecía activo con 27/7.500 llamadas mostradas por su panel y una observación natural fresca de directo. El calendario reutilizó caché; el contador interno y el saldo del proveedor no coincidían. Hay que volver a leer panel/headers antes de mostrar cuota actual.
- The Odds API tenía credencial configurada, pero no se verificaron plan, saldo ni una llamada externa fresca en esa observación.
- TheSportsDB tenía clave configurada, pero no plan confirmado; la cola interna y el presupuesto/cooldown limitaban el trabajo fresco.
- Telegram estaba configurado; no se observó un recibo nuevo de entrega real.
- Stripe indicaba modo de prueba y el conector requería reautenticación; no se probó facturación real.

No se repitieron llamadas a esos proveedores para evitar consumo, notificaciones o cobros. Los estados deben actualizarse desde paneles autorizados y observaciones naturales, en vez de inferirse por el nombre de una variable o una respuesta cacheada.

## Primer lote local aplicado

1. **Escudo SVG:** se escapa el nombre accesible y las iniciales insertadas en el SVG, además de limitar el nombre de entrada a 120 caracteres.
2. **Restablecimiento de contraseña:** en producción ya no se genera un enlace de recuperación si SMTP no está configurado; el correo usa una URL HTTPS canónica configurada y nunca el `Host` recibido. Si falla el envío, el token queda invalidado. El enlace diagnóstico relativo solo existe en Local Safe.
3. **Creación del primer administrador:** `/admin-bootstrap` queda cerrado fuera de Local Safe/pruebas; evita permitir alta inicial anónima en producción.
4. **Credencial de automatización:** se acepta solo por cabeceras (`X-Automation-Secret` o `X-CRON-SECRET`), no en URL, formulario o JSON.
5. **Evento público de analítica:** se rechaza un cuerpo ausente o mayor de 16 KiB antes de parsear JSON.
6. **Agenda de Inicio en escritorio:** las competiciones próximas pasan a dos columnas a partir de 1.101 px y los partidos usan el ancho disponible; en móvil permanecen apilados. No se cambiaron logos.

La configuración versionada de Render web incluye ahora el origen público HTTPS conocido para los correos de recuperación. Este cambio solo está en el checkout: no modifica el entorno de Render hasta una sincronización/despliegue autorizados.

Estos son arreglos de código local, no cambios de producción. La creación de administradores y recuperación de contraseña merecen una revisión de despliegue/entorno antes de publicar. Las rutas heredadas de automatización deben permanecer cubiertas por sus pruebas de transporte.

## Validación local ejecutada

- Pasaron 11 archivos de pruebas enfocados, incluidos los nuevos `tests/test_first_batch_security_fixes.py`, el recorrido de Inicio `tests/test_home_matchday_browser.py`, auth/admin, crecimiento, transporte del Cron, membresías, entrega de recursos, verbos de mutación y deduplicación de backups. Tras el último ajuste, la suite nueva volvió a pasar (8 casos) y los recorridos de Inicio/escudos pasaron 26 casos de navegador y servidor.
- El recorrido de navegador usa datos deportivos sintéticos, bloquea llamadas externas y verifica escritorio, móvil y anchura estrecha; la agenda queda en dos columnas en escritorio y una en móvil sin desbordamiento horizontal.
- `node tools/build_visual_css.mjs --check`, `git diff --check` y `py_compile` pasaron después del último ajuste. El CSS mantiene sus fuentes generadas.
- `render.yaml` se volvió a parsear y validar contra el esquema JSON oficial actual de Render. No se llamó al validador de Blueprint de Render ni se sincronizó el manifiesto.
- Las pruebas no ejecutan pagos, llamadas a API deportivas, mensajes Telegram ni operaciones de backup en producción. No son una certificación de los recorridos autenticados de producción.
- La auditoría de seguridad formal de repositorio completo sigue incompleta. La revisión manual de este lote localizó y cubrió los límites descritos; no debe presentarse como análisis completo de los 4.486 archivos rastreados.

## Prioridad de evolución recomendada

### P0 — Confianza y control

1. Revisar y terminar el lote local de seguridad; correr la matriz de pruebas aplicable y solo después solicitar autorización de publicación.
2. Separar el rol de membresía del rol laboral. Diseñar permisos mínimos por operación; OWNER exclusivo para facturación, secretos, cambios de rol, expulsiones y automatizaciones críticas. Añadir credenciales individuales, contraseña temporal, cambio obligatorio, registro de acciones y revocación de sesión.
3. Instrumentar los backups por etapa (bloqueo, recuperación, snapshot, integridad, hash, manifiesto y publicación), con una reproducción local representativa. No relajar verificaciones ni usar producción como laboratorio.
4. Mostrar la verdad del dato deportivo: proveedor, competición/partido, hora de origen, hora de sincronización, caché, campos disponibles y motivo de ausencia.

### P1 — Valor diario para el cliente

1. Calendario/Directo con equipos y ligas favoritos, filtros y densidad ajustada a PC/móvil.
2. Estadísticas en directo solo cuando el proveedor las ofrece para ese partido; posesión, tiros, faltas, córners, alineaciones y mapa de zonas deben llevar fuente y hora, o explicarse como no disponibles.
3. Pronósticos y combinadas con trazabilidad de cada dato y evaluación histórica reproducible. Separar cuotas actuales de pronóstico del motor y evitar presentar contenido no validado como sugerencia.
4. Highlights con estado de disponibilidad, licencias/revisión y enlace comprobado; informar claramente cuando no hay resumen.

### P1 — Centro de Mando y negocio

1. Panel único responsive que muestre salud por proveedor, última llamada real, frescura, error, cuota con fuente y hora, última sincronización y coste solo cuando esté verificado.
2. Probar cada operación del panel con identidad/rol autorizado, confirmar resultado y dejar auditoría legible. Replicar capacidad de PC en móvil sin agrandar privilegios.
3. Verificar membresías/Stripe en modo de prueba antes de habilitar cobros; analizar publicidad FREE y rentabilidad con métricas reales, consentimiento y derechos. No conectar campañas ni cobros durante una auditoría.

### P2 — Mantenimiento y presentación

1. Reducir deuda del monolito de Flask por dominios graduales, sin rehacer el producto ni sustituir SQLite sin un caso de escala demostrado.
2. Mantener un índice compacto para documentación viva; conservar informes antiguos en histórico.
3. Evolucionar el sistema visual por componentes (tipografía, espacios, estados vacíos/errores, contraste, densidad y responsive). No rediseñar logos en este lote.

## Qué significa “listo” en los siguientes lotes

Cada mejora debe tener: fuente o permiso verdadero, prueba automatizada, recorrido realista en PC y móvil, estados vacío/error/caché, autorización de servidor cuando modifica datos, observabilidad sin secretos, revisión de regresión y evidencia del despliegue posterior. Un módulo importable, una pantalla o un HTTP 200 no bastan para llamarlo listo para clientes.

## Acciones no realizadas

No hubo commit, push, merge, deploy, cambio de secretos, llamada a API externa, mensaje Telegram, cobro, modificación del disco, limpieza de ramas/worktrees ni operación sobre datos de clientes. Los cambios descritos siguen pendientes de revisión y autorización antes de salir de este checkout.
