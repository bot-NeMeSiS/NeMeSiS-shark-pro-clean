# V941 · Integración del centro de mando Admin

Estado: documentación de la integración local. La aprobación de pruebas, navegación real y ZIP se registra por separado; este documento no certifica producción.

## Base comprobada

La carpeta oficial es `C:/Users/aloha/OneDrive/Escritorio/NeMeSiS shark pro`. El preflight encontró `V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL` en `VERSION.txt`, `APP_VERSION` y la asignación de `app.py`. V941 es el incremento solicitado. Las comprobaciones y documentos históricos conservan su versión de origen.

El destino conserva las entradas existentes `/admin/dashboard` y `/admin/control-center`, la plantilla `templates/admin_dashboard.html`, la navegación canónica `templates/components/v933_navigation.html` y las sesiones Admin. No se crea otra aplicación, otro Company OS ni otro Sentinel.

## Fuentes reutilizadas y responsabilidad

| Componente existente | Integración y límite |
| --- | --- |
| `engines/company_operations_center_engine.py` | Lectura de incidencias y evidencias operativas; sigue siendo el origen del centro de operaciones. |
| `engines/admin_operations_workbench.py` | Presentación de tareas y registro de herramientas conocidas; no consume proveedores ni resuelve incidencias al dibujar el panel. |
| `engines/company_intelligence_engine.py` | Inteligencia corporativa existente, accesible desde el centro unificado. |
| `engines/company_operating_system_engine.py` | Company OS existente; no se duplica su modelo de empresa. |
| `engines/continuous_shark_sentinel_engine.py` | Continuous Sentinel conserva su ciclo y evidencias. Su página histórica no equivale a una certificación reciente. |
| `engines/sentinel_autopilot_engine.py` | AutoPilot existente; el nuevo panel no instala otro planificador. |
| `engines/sentinel_issues_engine.py` | Memoria de incidencias reutilizada para mejoras; no se crea un segundo registro de incidencias. |
| `engines/shark_ai_product_assistant_engine.py`, `engines/shark_engine.py` | SHARK de producto se mantiene. El copiloto Admin se alimenta de contexto administrativo y un catálogo explícito de propuestas. |
| `engines/stripe_payments_engine.py`, `engines/payment_readiness_engine.py` | Pantallas de pagos y readiness existentes. Abrir el centro no cobra, no modifica suscripciones y no valida un webhook remoto. |
| Motores Telegram existentes | Cola, formatos, fiabilidad y revisión siguen en sus componentes. No se autoriza un envío por formular una pregunta. |
| `tools/local_desktop/run_local_desktop.py` | Preparación local aislada con datos de QA rotulados; no toca cuentas reales. |

## Integración nueva

`blueprints/admin_master_control.py` integra las rutas protegidas, snapshots locales, callbacks existentes y preview. `engines/admin_control_engine.py` concentra el catálogo de acciones permitidas, configuración operativa y propuestas confirmables. Reutiliza `automation_state` para ajustes con prefijo `admin_control.settings.`; registra propuestas y un historial de acción en `admin_action_proposals` y `admin_action_audit`. El texto del usuario no se convierte en nombres de funciones, comandos, importaciones ni SQL.

Una propuesta tiene propietario, caducidad, versión de aplicación y revisión de ajustes. El servidor vuelve a comprobarlos al ejecutar. El catálogo contempla ajustes y restauración, sincronización deportiva, diagnóstico Telegram, reintento de Telegram, análisis Sentinel e incidencia de mejora. La existencia de una entrada en el catálogo no certifica que su adaptador esté habilitado ni que una operación externa se haya ejecutado.

El flujo de SHARK es contexto → explicación → propuesta → confirmación separada → resultado → auditoría. Cuando falta evidencia, debe expresarlo. La hora de lectura del panel no sustituye la fecha de la última ejecución de un proveedor.

El preflight no encontró un cliente de inferencia OpenAI conectado al flujo administrativo. V941 incorpora `admin_openai_answer` dentro del motor SHARK existente: consulta Responses solo bajo demanda, con clave y modelo configurados, tema clasificado y pregunta fija junto con cifras/estados agregados permitidos (sin enviar el mensaje libre del administrador), sin herramientas ni autoridad para ejecutar acciones, límite de respuesta y retorno al diagnóstico determinista cuando falla. LOCAL SAFE impide esta consulta. La integración externa no se ha probado con credenciales reales; configurado no equivale a disponible ni a una respuesta remota realizada.

## Límites y verificación

El registro del motor describe el riesgo alto de reintentar Telegram, pero el adaptador V941 excluye esa acción de la interfaz y rechaza sus propuestas: el reintento se remite al Command Center existente porque procesar toda la cola podría enviar entradas ajenas. Cobros, secretos, despliegues y acceso remoto no se prueban mediante acciones reales. Las pruebas de callbacks usan dobles controlados. La preview de cliente debe mantenerse aislada de la cuenta real y de los cambios de plan.

La QA estática de `tools/check_admin_master_control.py` no importa `app`: verifica identidad, plantillas, recursos y destinos de navegación. Se ejecutó con resultado 8/8 aprobado. La última suite pura de acciones y SHARK tiene 98 pruebas aprobadas con callbacks controlados (registro, identidad, caducidad, concurrencia, idempotencia, auditoría, reversión y frontera de datos IA). La QA funcional usa LOCAL SAFE con base temporal. La QA de navegador debe guardar capturas reales y dimensiones; no se declara paridad visual ni pixel perfect sin inspección.




## Addendum: SHARK Reliability & Learning Center (pendiente de implementar)

Alcance incorporado el 2026-09-23. Esta seccion es diseno/aceptacion basado en inspeccion de codigo, NO funcionalidad entregada. Sigue vigente el bloqueo de desarrollo mayor hasta CI de PR91 y reconciliacion PR90; no modifica el parche aislado db3670e7 ni autoriza push/deploy.

### Reutilizacion y brechas observadas

- sentinel_issues_engine.py ya tiene issue_fingerprint, upsert, primera/ultima aparicion, contadores, verificacion e historial. Extender este registro canonico; no crear otra tabla/archivo de incidentes paralelo. Su fingerprint actual combina stable_key o area/ruta/archivo/titulo/evidencia; revisar datos variables y sanitizacion antes de generalizarlo. Un hash no elimina secretos de los datos originales ni demuestra identidad de causa.
- update_issue_status admite RESOLVED sin exigir un contrato de verificacion completo. Implementar posteriormente validacion central para todos los caminos de cierre, conservar compatibilidad/historial y marcar evidencia antigua no certificada sin inventarla.
- sentinel_improvement_workflow_engine.py ya agrupa incidencias y genera tareas/prompts. Extender metadatos de causa, hipotesis, PR/SHA, tests, prevencion, deteccion y resultado, evitando otra cola.
- sentinel_render_alignment_engine.py compara versiones y devuelve aligned. Esto NO basta para ALIGNED_CONFIRMED por SHA. Unificar con el diagnostico de release del Master Control; no heredar ese booleano como certificacion de despliegue.
- static/pwa-install.js ya usa beforeinstallprompt/appinstalled, guia iOS y standalone. Actualmente termina al detectar Admin o standalone; revisar la integracion con Admin y la indicacion de instalada. Cancelar consume deferredPrompt y la UI puede reaparecer sin otro evento: verificar que no deje un boton inutil.
- tests/test_pwa_easy_install.py contiene una expectativa literal NEMESIS_CACHE_V940_ICON_ mientras el borrador V941 usa V941. Es un contrato pendiente de reconciliar y probar, no un fallo ya reparado. Las comprobaciones de texto no certifican instalacion real.

### Contratos de implementacion y aceptacion

1. Memoria: preservar incident_id y fingerprint versionado; categoria/superficie, primera/ultima deteccion, recuento, sintoma, causa confirmada separada de hipotesis, PR/commit/archivos/tests/reglas/detectores, estado, resolucion y verificacion. Sanitizar por allowlist antes de persistir. Deduplicar el mismo evento/ciclo; una recarga no aumenta frecuencia. Migracion aditiva e idempotente.
2. Conocimiento SHARK: MATCH CONFIRMADO solo con evidencia suficiente de identidad; SIMILITUD, POSIBLE RELACION y SIN RELACION CONOCIDA son categorias distintas. Referenciar evidencia y limitaciones, sin porcentajes inventados ni aprendizaje automatico de causas supuestas.
3. Radar determinista: usar fuentes locales existentes de jobs, sincronizacion, colas, proveedores, caches, runtime, release y tests. Cada aviso incluye evidencia fechada, umbral/motivo y acciones permitidas. Sin datos o sin expectativa de frecuencia -> DESCONOCIDO; no cero ni NORMAL. Detectar trabajos atrasados, datos antiguos, repeticiones, fallos tras fix y despliegue no certificado.
4. Alertas tempranas: NORMAL / OBSERVAR / ATENCION / RIESGO ALTO / INCIDENTE / DESCONOCIDO. Crecimiento durante tres ciclos exige tres observaciones reales comparables; no inferir tendencia de un snapshot. Mostrar ventana y cobertura. No asegurar que Telegram funciona por haber funcionado antes.
5. Prevencion/acciones: registro existente, propuestas y auditoria del Master Control. Reintentos acotados/idempotentes, permisos y comprobacion posterior. No activar self healing externo de forma implicita. Queue/Telegram/sync requieren clasificar efectos antes de habilitar; no asumir reversibilidad. No pagos, SQL libre, shell, codigo, secretos o deploy.
6. Verificacion: comprobar exactamente la condicion original en el SHA/entorno indicado; guardar resultado y evidencia. Prueba roja antes/verde despues cuando reproducible. Ausencia de deteccion no equivale a resolucion. Reaparicion conserva y reabre el mismo incidente cuando corresponda.
7. Drift: comparar main SHA, PR HEAD, build SHA, Render SHA, runtime version y APP_VERSION segun rol/entorno objetivo, fuente y fecha. PR HEAD diferente de main no es por si solo un fallo de produccion. ALIGNED_CONFIRMED / MISALIGNED_CONFIRMED / UNKNOWN / ERROR. Version igual sin SHA suficiente -> UNKNOWN; health200 nunca certifica.
8. Riesgo del cambio: mapa trazable de archivos/componentes, dependencias, incidentes y tests. Mostrar evidencia/alcance desconocido; no afirmar un numero de tests o dependencias por conjetura. Reutilizar la evidencia deportiva de PR90 y mantener calendar/live/picks/team form/Madrid Time coherentes.
9. UI: una seccion Fiabilidad del Admin canonico con estado, radar, incidentes/repeticiones, protecciones, advertencias, historial/cambios y conocimiento. Timeline solo de eventos reales con fuente y hora Madrid. Resumen diario bajo demanda con datos disponibles; sin envio automatico ni llamadas externas al abrir.
10. PWA: una web/PWA PC y movil. Verificar manifest, HTTPS, iconos, start_url, scope, standalone, service worker, actualizacion/version de cache y proteccion de contenido privado. Boton solo con instalacion disponible; estado instalada solo con evidencia soportada; instrucciones breves cuando corresponda. Cancelacion/error no debe dejar un boton inerte. Probar Windows Chrome, Windows Edge y movil compatible; distinguir simulacion de eventos, Chromium automatizado e instalacion real. No .exe ni afirmaciones de anclaje al SO no comprobadas.

### Verificacion pendiente

Pruebas de no-cierre sin evidencia, sanitizacion, fingerprint estable y sin colisiones semanticas conocidas, deduplicacion por evento, recurrencia tras fix, unknown/zero, cache/actualidad, tendencia insuficiente, SHA ausente/contradictorio, permisos/CSRF, acciones aprobadas/idempotentes, rechazo de acciones arbitrarias y PWA instalada/cancelada/no compatible/actualizacion. Reutilizar suites existentes y anadir reproducciones significativas, sin tests que solo reflejen la implementacion.

La auditoria de instalacion real, el radar, la nueva seccion y el enforcement de cierre NO se han implementado ni validado en este addendum. El ZIP anterior sigue provisional. Las guias internas se actualizan en CODEX_DAILY_AUTOMATION_GUIDE.md sin mezclarlas con la reparacion PR91.
