# Cobertura incremental de highlights

El catálogo descubierto de vídeos es independiente de la cobertura de partidos.
El denominador de cobertura contiene todos los partidos canónicos finalizados
con identidad suficiente y final confirmado según el contrato deportivo existente.
Un resultado del proveedor vacío cuenta como comprobación, nunca como licencia.

## Ejecución y persistencia

El único Cron maestro conserva `/api/automation/highlights/sync`. La ventana
reciente de siete días mantiene su frecuencia existente. Cuando ese carril está
en caché, el mismo endpoint avanza el inventario y un lote histórico sin refrescar
la ventana ni añadir otro programador. Se inventarían 200 filas por cursor y hasta
200 partidos adicionales nuevos/finalizados/remapeados por ejecución. El cursor
no se reinicia; el anti-join detecta filas antiguas que cambian posteriormente.

`highlight_coverage` guarda una fila por partido, identidad, estado, fecha de
comprobación, evento, vencimiento del reintento y lease de 90 segundos. Un cambio
de identidad invalida la evidencia y los contadores inmediatamente. Los leases
impiden ejecución concurrente y un proceso antiguo no puede cerrar otro lease.

Estados: UNSCANNED, CHECK_PENDING, CHECKED_NO_VIDEO, VIDEO_FOUND, LINKED,
RETRY_LATER, AMBIGUOUS, PROVIDER_ERROR. La cola distingue descubrimiento de la
revisión de derechos. Los estados de cobertura no conceden permiso de publicar.

El lote histórico valida el evento mediante la reconciliación estricta existente
(equipos, fecha Madrid y competición), guarda esa identidad en caché durante
90 días y consulta Premium V2 `lookup/event_highlights/{idEvent}`. Si falta el ID,
la consulta dated existente exige la misma identidad exacta. Duplicados o
ambigüedades no se fuerzan. Respuestas incorrectas no cuentan como NO_VIDEO.

## Prioridad, caché y consumo

El carril reciente precede al histórico. El histórico prioriza partidos aún no
comprobados y el peso editorial deportivo existente; después antigüedad del
aplazamiento y fecha. Máximo un partido histórico por ejecución. Los resultados
vacíos se reintentan a seis horas para recientes, tres días para 8–30 días y
30 días para históricos; tras varias comprobaciones históricas, 90 días.

La caché V2 y los feeds persisten en `sportsdb_highlight_feed_cache`. El backfill
usa el mismo límite de 12 llamadas por operación, además de una reserva atómica
persistente de 12 llamadas por ventana de seis horas (como máximo 48 por día UTC; no es
una cuota contractual del proveedor). Histórico: máximo dos llamadas por esa
ventana, dentro de las doce, para preservar el carril reciente. Se reserva ANTES
de HTTP y no se reembolsa tras un error/reinicio. Nunca toca las 60 llamadas/día
de recuperación pospartido. No cambia planes, claves ni recursos de Render.

## Lecturas y cliente

Command Center y `/api/admin/highlights/readiness` leen sin migraciones, escrituras
ni consultas al proveedor. Elegibles/comprobados/pendientes y porcentaje se miden
sobre partidos, no sobre vídeos. También muestran estados, cursor y próximo lote.
Sin una lectura verificable se muestra desconocido, no cero inventado. Los
contadores de autorización existentes siguen indicando su alcance de muestra.

Las colecciones de cliente se enriquecen por IDs canónicos en lotes de hasta
500, reutilizando el mismo read model y policy engine. La marca compacta
`▶ Resumen disponible` sólo aparece para contenido autorizado y con highlights
activados. El reproductor permanece en Match Center. No hay descarga, rehosting,
autorización masiva ni trabajo manual rutinario.

## Resultado técnico del Cron

PASS: solicitudes y almacenamiento correctos, aunque NO_VIDEO/NO_STATISTICS o
derechos pendientes. Los reintentos siguen visibles; una respuesta vacía no
consume el contador de errores y no se pierde tras cinco intentos.
PARTIAL: presupuesto, dependencia en espera o datos efectivamente incompletos.
FAIL: HTTP, autenticación, almacenamiento, respuesta inválida o error real de
ejecución. Los demás carriles continúan aunque uno falle, y el resultado global
refleja ese error. Compatibilidad de endpoints y campos antiguos preservada;
`technical_status` y `content_pending` hacen explícita la separación.
