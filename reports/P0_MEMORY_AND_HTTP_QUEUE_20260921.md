# Rapidez, memoria y cola HTTP — 21/09/2026

## Base y estado real

Extensión controlada de PR63, base publicada PR62 `2e7bcbedbd28d0be2761ae297ca211f4e8b915e6`. Conserva los cinco archivos y las reglas de verdad/caducidad ya revisados. No incorpora PR59/PR60.

La observación de PR62 ya terminó: Guard `35646915709`, job `106490148456`, SUCCESS. Artefacto `10662529623`, SHA256 `4eb61a07af4fef6247e143a2f13702fa877b711bb057f3e019990f912ebf6fd2`, contiene `PRODUCTION_QUALITY_SENTINEL.json`: PRODUCTION_CERTIFIED, SHA exacto, doce controles PASS, ningún fallido o ausente y rollback_recommended=false.

Tiempos de esa muestra de navegador (networkidle, NO LCP/INP/p95): Inicio 2545 ms; Calendario 2856; Directo 1889; Picks 2052; SHARK 2269; Track Record 3264; ficha de partido 1447; equipo 2128; competición 2218; Inicio móvil 1868. No es una comparación A/B bajo condiciones iguales ni prueba de que cada visita futura dure eso. No cierra por sí sola los 502 históricos ni los datos deportivos incompletos.

Render: tras llegar a 442802180 bytes a las 20:25 UTC, las muestras 20:30–20:50 permanecen entre 437305340 y 438431740 bytes; límite observado 536870900. Memoria alta que se estabiliza en ese intervalo, no evidencia suficiente de fuga/OOM. Sin nuevos 502 en las muestras posteriores al intervalo 19:50 devueltas hasta 20:50 UTC. No se reinicia ni escala para maquillar esta lectura.

## Defecto corregido: conexiones de observabilidad

En `engines/observability_engine.py`, siete usos de `with _connect(db_path)` completaban la transacción, pero no cerraban la conexión SQLite. La documentación de Python distingue ambos comportamientos. Se envuelven con `closing`, manteniendo el contexto transaccional interno, commits, rollback, consultas, esquema y respuestas originales. `_connect` conserva su firma y devuelve una conexión normal.

Reproducción local en DB temporal: cuatro visitas a Observabilidad abrían 16 conexiones sin cierre explícito. El recolector podía liberarlas después; no se afirma que quedaran abiertas permanentemente. Tras el cambio, las 16 se cierran antes de finalizar el recorrido. Perfil de ocho visitas alternadas Observabilidad/Founder: 74 conexiones abiertas, antes 58 cierres explícitos y después 74; cero conexiones externas intentadas. El perfil cliente separado (20 peticiones a runtime/Directo/Calendario/Picks/Home) cerró correctamente sus 38 conexiones ya en la base: NO se atribuye este defecto a todas las pantallas.

Las cifras RSS de procesos locales separados no se usan para prometer una reducción de memoria en Render. Este arreglo asegura liberación determinista de recursos, no demuestra que explique los 438 MB de producción.

23 nuevas regresiones: cierre al salir, excepciones de creación/lectura/escritura/commit, rollback sin inserciones parciales, persistencia y detalle de errores, 40 resúmenes con 160 conexiones retenidas por el test y 15 resúmenes concurrentes con 60 conexiones independientes cerradas por su hilo propietario. Ocho contraejemplos fallan sobre el original y pasan con el arreglo.

Un primer test intentó consultar desde el hilo principal conexiones creadas en otros hilos y falló correctamente por check_same_thread. El verificador ahora registra el cierre efectivo en el hilo propietario y comprueba la operación sobre conexiones del mismo hilo. No se ha cambiado check_same_thread ni la protección del código productivo.

## Experimento de cola, NO configuración productiva

`tests/test_server_queue_isolation.py` arranca un servidor aislado con la aplicación real, una DB temporal y credenciales efímeras. Mantiene la ruta protegida `/api/automation/sports/sync`, pero sustituye exclusivamente su tarea deportiva por una espera sintética liberada por el test. Las conexiones salientes del servidor están bloqueadas; se usa HTTP de loopback, nunca Render/proveedores. Comprueba 403 sin secreto y que la tarea no se inicia en ese caso.

Se observa si `/live` responde ANTES de liberar la tarea. Dos casos locales de Werkzeug demostraron que el servidor serial espera y el threaded progresa. Werkzeug usa hilos por petición; NO se presenta como prueba de Gunicorn con dos hilos. Dos casos adicionales usan la dependencia productiva Gunicorn, un proceso y sync/1 frente a gthread/2. Gunicorn no estaba instalado localmente y su descarga no fue posible: esos casos fallan por dependencia ausente en el entorno local CI, no están certificados allí. Deben pasar sin omisiones en el Smoke de GitHub, donde requirements.txt sí instala Gunicorn. No se modifica el workflow para omitirlos.

El experimento mide orden de finalización, no una mejora porcentual de latencia ni la seguridad de todas las operaciones concurrentes. No se activa gthread en Render. Cambiar esa configuración todavía requiere validar sesiones simultáneas, contención real de DB, deduplicación de cron y memoria con carga representativa.

## Validación y puerta de integración

Selección local ampliada: 257 PASS y ocho casos integrales no certificados; tras preparar local_dev y usar Chromium instalado, esos ocho devuelven ERR_BLOCKED_BY_ADMINISTRATOR. Se conservan los fallos, sin modificar pruebas/políticas. Las 23 pruebas nuevas de recursos pasan; dos experimentos HTTP locales pasan y dos de Gunicorn quedan pendientes del CI por dependencia. No sumar los 23 otra vez a los 257.

Compilación de los archivos nuevos y Madrid PASS. Escáner existente: 1205 archivos, cero hallazgos; sin exclusiones ni cambios al escáner. Los tres blobs de código/pruebas coinciden con los bytes locales revisados.

Exigir QA, Preflight y Smoke completos del NUEVO HEAD de PR63, incluido Gunicorn, antes del merge normal. La certificación previa de PR62 ya terminó, pero no se transfiere automáticamente a este código. Tras integración: único Auto Deploy, verificar SHA Web/Cron y completar nueva observación; mantener #61 abierta para estabilidad sostenida. No modificar planes, variables, cuotas, usuarios, pagos, Telegram, TTLs, datos productivos o /data. Sin mejoras visuales nuevas ni capturas ficticias.
