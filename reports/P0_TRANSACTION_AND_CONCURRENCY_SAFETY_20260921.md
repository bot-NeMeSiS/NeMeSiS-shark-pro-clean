# Transacciones, presupuesto y sesiones simultáneas — 21/09/2026

## Base y límites de publicación

Base exacta publicada: PR63, `efd8eee4ebcb5a21324a575e2c801c93eaf4a5d0`.
No se incorpora PR59 ni PR60. No se modifican app.py, workflows, configuración
Gunicorn/Render, planes, usuarios/productivos, pagos, proveedores o TTLs.
Es una preparación de seguridad para concurrencia, NO una activación de gthread
ni una afirmación de navegación instantánea.

El servicio Render `telegram-auto-tick` ejecuta `tools/render_cron_master_tick.py`,
que usa el recorrido Telegram + evolución continua. El defecto transaccional
reproducido está en el motor diario V818 accesible por `/api/automation/master-tick`.
No se atribuye a este defecto toda la latencia del cron actualmente programado.

## Tres contraejemplos reproducidos sin red ni datos reales

1. Una tarea sintética del master intenta escribir con su propia conexión SQLite:
   el código original devuelve `database is locked`, aun con un único llamante,
   porque el master mantiene otra transacción de escritura abierta. El candidato
   completa la escritura. No se usa un timeout reducido de prueba como medida de
   mejora de latencia de producción.
2. Con otra escritura abierta, el guard original devuelve `ok=true` aunque no
   consiguió registrar su reserva de presupuesto. El candidato devuelve
   `api_budget_storage_unavailable` y no autoriza el trabajo.
3. Una simulación original reserva la clave diaria de una tarea y puede impedir
   la siguiente ejecución real. El candidato registra la simulación sin reservar
   la tarea ni gastar presupuesto. Las claves reales existentes no se eliminan.

La base previa de los dos módulos coincide con los blobs remotos:
- daily_automation_engine.py: `cf635d4cf8b120bde4ecc6f332ca9b9816f42e97`.
- api_usage_guard_engine.py: `35ecdaa0a41cea10a2882eb507839cc770ba8c9e`.

## Cambios

El master usa transacciones cortas para preparar esquema, reclamar una tarea y
registrar el resultado. No mantiene un bloqueo de escritura mientras llama al
guard ni mientras ejecuta una tarea. Las reservas diarias se confirman ANTES del
callback. Si este falla o el proceso se interrumpe después, no se libera la
reserva ni se repite automáticamente una posible acción externa. La evidencia
de tareas ya completadas queda persistida aunque falle una tarea posterior.
Los contadores no se adelantan a una escritura de auditoría fallida.

La simulación consulta una reserva existente para no afirmar falsamente
`would_run=true`. Sigue escribiendo auditoría DRY_RUN: no es un modo de lectura
pura de la DB. Se conserva el comportamiento explícito previo de force=True.

El guard de cuota obtiene lectura, decisión e inserción bajo BEGIN IMMEDIATE,
y devuelve autorización solo tras el commit. Las denegaciones registran cero
consumo, conservando en details_json la cantidad solicitada. El resumen deja de
sumar denegaciones históricas y valores negativos. La reserva usa el presupuesto
del mapping env explícito y un solo día Madrid; no mezcla env con os.environ.
Entradas inválidas/negativas/bool y proveedores desconocidos no autorizan.
Un error de almacenamiento no se traduce en permiso ni expone rutas/SQL.
La cuota sigue siendo una ESTIMACIÓN local, no saldo confirmado del proveedor;
no cubre automáticamente llamadas hechas fuera de este guard.

Se cierran explícitamente las conexiones propiedad de ambos módulos después de
sus contextos transaccionales, incluidos retornos anticipados y excepciones.
No se modifica check_same_thread ni el gestor general database_manager.

## Pruebas y alcance

34 nuevas regresiones en tres archivos. Selección local amplia: 345 casos,
337 aprobados y 8 navegaciones de navegador sin certificar localmente por
entorno (binario esperado/directorio ausente). Un reintento con Chromium instalado
y el directorio local_dev habitual devolvió ERR_BLOCKED_BY_ADMINISTRATOR; no se
eliminan los casos ni se alteran políticas. Smoke remoto debe correr su suite
normal completa sobre el HEAD exacto.

Ocho casos elegidos fallan en la base original; se conserva la salida fallida.
Pruebas nuevas: DELETE/WAL, guard antes del callback, dry-run/force, fallo de
callback/auditoría/commit, rollback y persistencia, cierre de conexiones, seis
llamantes sobre una tarea diaria, doce reservas simultáneas para un presupuesto
de cinco, y cuatro procesos independientes reservando en el mismo archivo.
La ejecución multiproceso no implica múltiples workers productivos.

Dos pruebas Flask de peticiones concurrentes comprueban separación de sesiones,
CSRF, favoritos y conexiones query-only con dos usuarios sintéticos. Cada cliente
conserva solo sus favoritos, ignora el user_id ajeno del payload, rechaza el token
de la otra sesión y no modifica el rol de la otra cuenta. No es prueba en teléfonos
reales ni certificación de todos los endpoints bajo Gunicorn multihilo.

## Bloqueos antes de activar concurrencia o publicar el conjunto

- La observación productiva de PR63 seguía activa al iniciar esta intervención.
  No cancelarla con otro merge. No reutilizar como certificación el éxito PR62.
- Las tareas ALWAYS y force conservan su contrato previo; no se ha certificado
  que todos sus callbacks toleren ejecuciones simultáneas ni se proporciona una
  garantía global exactly-once. Mantener el worker actual hasta revisar exclusión
  de ejecuciones reales y todos los caminos del cron programado.
- Liberar la transacción permite ejecutar callbacks antes bloqueados: revisar
  especialmente el reconciliador de ciclo de vida heredado antes de integrar.
  Esta entrega no cambia su SQL ni certifica que represente la verdad canónica
  de cada estado deportivo. No ejecutar recuperación o envíos reales para probarlo.
- #61 permanece abierta. No hay causalidad demostrada para RSS ni 502 históricos.
  Nuevas muestras Render 21:20–21:40 UTC: memoria ~237–268 MB, un 502 en el primer
  intervalo y cero en los posteriores devueltos; no prueban mejora causal ni
  ausencia de problemas bajo tráfico real.

Referencias técnicas: SQLite lang_transaction/isolation (un escritor por archivo,
WAL no proporciona dos escritores simultáneos); Python sqlite3 context manager
(commit/rollback no equivale a close). No se cambia el motor de base de datos.
