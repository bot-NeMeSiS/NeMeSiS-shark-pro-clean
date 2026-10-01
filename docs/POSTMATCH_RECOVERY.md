# Recuperación pospartido y resúmenes por encuentro

Dos tareas persistentes en SQLite, coordinadas por el Cron existente. Pausadas por defecto: importar, desplegar y abrir pantallas no activa consultas ni concede derechos.

## Alcance
- Finales confirmados de los últimos siete días: dos tareas por identidad del partido.
- Estadísticas mediante endpoints oficiales de API-Football y TheSportsDB, solo las fuentes activadas. Sin scraping de páginas, sin nuevas suscripciones ni claves.
- Resúmenes mediante el evento de TheSportsDB; se reutilizan catálogo, asociación y revisión existentes. Encontrar una URL no autoriza su publicación. No se descargan vídeos.
- Siete métricas básicas completas por ambos equipos para marcar recuperación completa; fuentes con cobertura parcial permanecen parciales. Los nulos no se convierten en cero. No se calcula ni inventa xG.
- La ficha muestra estado de vídeo, carga por acción expresa y enlace externo cuando está permitido. No se certifica reproducción al recibir HTTP 200 ni al crear un iframe.
- Datos seleccionados con origen, referencia, periodo y momento de observación. Conflictos requieren decisión administrativa con control de revisión y bloqueo de valores elegidos. Las observaciones y selecciones anteriores quedan auditadas.
- No cambia marcadores, apuestas publicadas, Stripe, miembros ni envíos de Telegram.

## Operación
Tras integrar y verificar el despliegue, abrir `/admin/highlights-review`, sección **Trabajadores pospartido**. Revisar el permiso de reutilización y cobertura del plan real, elegir fuentes ya configuradas y confirmar un límite diario adicional (60 por defecto, máximo 200). Activar expresamente.

El Cron llama POST `/api/automation/postmatch/tick` con `X-Automation-Secret`. Sin cabecera correcta, 403; sin activación, `SKIPPED_DISABLED` sin escritura ni llamadas externas. `?dry_run=1` es lectura; jamás se acepta el secreto por URL en esta ruta.

Lotes de dos tareas como máximo, con presupuesto de 20 segundos y solicitudes acotadas. Reserva de cuota anterior a la petición. Reintentos a 30 minutos, 2, 12 y 48 horas; máximo cinco intentos por tarea antes de revisión/reapertura explícita. Bloqueos temporales de fuentes ante denegación, cuotas o errores repetidos. La clave del presupuesto usa el día de Madrid; este límite adicional NO representa la cuota total de la cuenta del proveedor.

Una sola ejecución con arrendamiento de 90 segundos; escrituras finales vinculadas al token de ejecución y a la identidad actual. No se mantiene bloqueo SQLite durante I/O externo. Reinicios, cambios de fecha/equipos y pausas invalidan escrituras antiguas. Las aprobaciones de vídeo se revocan si cambia el contenido o la asociación; las de imagen no se heredan al cambiar miniatura.

Diagnóstico protegido: `/api/admin/postmatch/status`. Incluye tareas, cobertura, motivos, cuotas locales y observaciones; excluye claves, tokens de arrendamiento y rutas de disco. Configuración, reintentos y revisión requieren administrador y CSRF. La supervisión puede consumir este estado sin habilitar reparadores autónomos.

## Verificación
```
python -m pytest -o addopts='' -q tests/test_postmatch_recovery.py tests/test_render_cron_master_tick.py
python tools/run_postmatch_browser_qa.py --output reports/postmatch_browser
```
El runner HTTP utiliza aplicación completa, base temporal y fixtures identificadas; bloquea destinos externos. `--snapshot` sirve únicamente para diagnosticar entornos que impiden navegación local: NO sustituye el control HTTP de CI. Ninguna prueba simulada demuestra acceso productivo a proveedores o reproducción real.

Antes de activar: comprobar los resultados de CI sobre el SHA de la PR y luego del despliegue; guardar copia recuperable de datos; ejecutar lote acotado y revisar un partido real con fuentes permitidas, atribución y cobertura. Aprobar vídeos solo con evidencia válida en el flujo existente. No marcar todos como autorizados ni atribuir automáticamente permisos por ser YouTube.

## Límites explícitos
No se garantiza vídeo o estadísticas para todos los encuentros. La API gratuita de TheSportsDB puede entregar solo una parte de las estadísticas. Las diferencias de alias no verificables quedan para revisión en lugar de emparejar de forma difusa. No se busca en cualquier sitio de internet ni se eluden accesos. No hay verificación automática infalible de bloqueo geográfico/reproducción ni descarga alternativa de vídeos retirados.

Para detener: desactivar en el mismo formulario; la siguiente comprobación del arrendamiento impide publicar resultados en curso. El estado y las observaciones se conservan. Revertir código no requiere borrar las tablas adicionales. No eliminar datos ni restablecer la base productiva para deshacer la activación.

Fuentes oficiales revisadas el 1 de octubre de 2026:
- https://www.thesportsdb.com/documentation
- https://www.thesportsdb.com/docs_terms_of_use.php
- https://www.api-football.com/documentation-v3
