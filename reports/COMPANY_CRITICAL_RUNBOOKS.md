# NeMeSiS SHARK PRO - Runbooks críticos

Todos los comandos deben ejecutarse con valores enmascarados, timestamps Madrid/UTC y acceso mínimo. Nunca imprimir secretos, cookies ni PII.

## RB01 - Render 502

- **Señal:** synthetic/usuario devuelve 502.
- **Primero:** `/api/runtime-version`, `/api/health`, logs de arranque y SHA.
- **No tocar:** DB disk, variables o plan sin diagnóstico.
- **Contener:** congelar deploy; página de estado.
- **Recuperar:** restart único si proceso colgado; rollback normal si coincide con deploy.
- **Validar:** home, login, DB read, calendar/live/picks, 0 5xx 30 min.
- **Rollback/cierre:** rollback si 502 persiste 10 min; cerrar con causa y SHA.
- **Evidencia:** deploy ID, logs redactados, tiempos y smokes.

## RB02 - Deploy fallido

- Señal: build/start rojo o runtime no cambia.
- Primero: comparar `origin/main`, deploy SHA y build logs.
- No tocar: DB, secretos, cache persistente.
- Contener: detener nuevos deploys.
- Recuperar: corregir pipeline o redeploy del SHA; rollback si arranca pero falla.
- Validar/cerrar: mismo SHA en runtime, checks y rutas críticas.
- Evidencia: workflow/deploy URL, SHA anterior/nuevo.

## RB03 - Rollback

- Señal: regresión P0/P1 ligada a commit.
- Primero: confirmar backup SHA y que DB schema no exige downgrade destructivo.
- No tocar: DB salvo runbook específico.
- Contener: anunciar mantenimiento/degradación.
- Recuperar: `git revert` o deploy de SHA conocido sin force push.
- Validar: runtime/SHA, auth, DB, datos, Telegram/Stripe en modo seguro.
- Cierre: 60 min estable y plan de forward fix.

## RB04 - DB bloqueada

- Señal: `database is locked`, p95 creciente.
- Primero: identificar writers, cron duplicado y transacciones largas.
- No tocar: WAL/SHM manualmente ni matar procesos al azar.
- Contener: pausar jobs no críticos y usar reads/fallback.
- Recuperar: dejar expirar lock, cerrar conexiones, retry con backoff.
- Rollback: código del writer causante.
- Cierre: 0 locks 30 min y prueba concurrente.

## RB05 - DB corrupta

- Señal: `integrity_check` falla.
- Primero: modo read-only, copia byte-a-byte y logs de disco.
- No tocar: no ejecutar repair sobre única copia.
- Contener: mantenimiento, pagos/Telegram/cron pausados.
- Recuperar: backup off-site validado en entorno aislado.
- Rollback: safety backup si restore nuevo falla.
- Cierre: integridad, recuentos, auth, memberships y reconciliación.

## RB06 - Restauración de backup

- Señal: pérdida/corrupción confirmada.
- Primero: elegir backup por timestamp, hash, integrity y RPO.
- No tocar: usuarios reales hasta doble aprobación.
- Contener: cerrar writes.
- Recuperar: safety snapshot, restore aislado, swap atómico.
- Rollback: volver al safety snapshot.
- Cierre: checks de negocio y firma de dos responsables.

## RB07 - API deportiva caída

- Señal: timeouts/429/5xx y sync fallida.
- Primero: proveedor, cuota, última sync y cache age.
- No tocar: no aumentar polling ni relajar filtros.
- Contener: backoff; servir cache etiquetada o vacío.
- Recuperar: sync incremental y dedupe.
- Rollback: configuración de ventana/proveedor anterior.
- Cierre: dos sync SUCCESS y frescura dentro de SLO.

## RB08 - Datos deportivos obsoletos

- Señal: edad supera ventana.
- Primero: comparar Madrid/UTC, provider timestamp, DB y cache.
- No tocar: no cambiar hora ni marcar fresh manualmente.
- Contener: excluir KPI/cards/APIs/SHARK/Telegram.
- Recuperar: sync autorizada, validación de completitud.
- Cierre: cero stale público y alerta resuelta.

## RB09 - Telegram caído

- Señal: delivery errors/cola crece.
- Primero: estado API, bot autorizado, destino enmascarado.
- No tocar: no reenviar masa ni rotar token sin causa.
- Contener: pausar worker y conservar dedupe IDs.
- Recuperar: dry-run, un mensaje técnico autorizado, liberar por lotes.
- Cierre: entregas sin duplicados y cola reconciliada.

## RB10 - Cron detenido

- Señal: heartbeat/last tick stale.
- Primero: schedule Render, auth header, logs y próximo tick.
- No tocar: no crear segundo scheduler.
- Contener: marcar datos stale; ejecución manual solo dry-run primero.
- Recuperar: corregir schedule/config y observar dos ticks.
- Rollback: configuración cron anterior.
- Cierre: last/next/result visibles y alerta verde.

## RB11 - SHARK lento

- Señal: mediana >1.5 s o p95 >2.5 s.
- Primero: medir 10 GET, DB reads/writes y llamadas externas.
- No tocar: no desactivar seguridad o calidad.
- Contener: modo seguro/cache; bloquear proveedor en render.
- Recuperar: eliminar N+1/write/red bloqueante.
- Rollback: SHA anterior si cambia contenido.
- Cierre: objetivos 30 min y mismo HTML funcional.

## RB12 - Stripe/webhook fallido

- Señal: webhook 4xx/5xx o pago no reconciliado.
- Primero: event ID, firma, idempotency y estado Stripe sin PII.
- No tocar: no cobrar/reembolsar manualmente.
- Contener: pausar checkout si estado incierto; conservar plan.
- Recuperar: replay firmado/reconciliación.
- Rollback: revertir entitlement solo con fuente Stripe.
- Cierre: Stripe=DB y evento 2xx una sola vez.

## RB13 - Membresía incorrecta

- Señal: plan visible no coincide con fuente.
- Primero: origen admin/purchase, expiry, event ID.
- No tocar: no borrar cuenta ni inventar pago.
- Contener: acceso provisional auditado si cliente pagó.
- Recuperar: reconciliar mapping y cache de sesión.
- Cierre: matriz de permisos y perfil correctos.

## RB14 - Secreto expuesto

- Señal: scanner/reporte/log confirma valor utilizable.
- Primero: clasificar sistema/alcance sin copiar valor.
- No tocar: no borrar evidencia ni publicar detalle.
- Contener: revocar/rotar, restringir repo/logs.
- Recuperar: actualizar env y servicios dependientes.
- Rollback: no se revierte una rotación; usar nueva credencial segura.
- Cierre: scan limpio, abuso evaluado, notificación legal si aplica.

## RB15 - Pérdida de persistencia

- Señal: DB vacía tras restart o mount ausente.
- Primero: `DB_PATH`, mount, tamaño e integrity.
- No tocar: no inicializar schema vacío ni reemplazar disco.
- Contener: mantenimiento y freeze de writes.
- Recuperar: remount o restore off-site con RB06.
- Cierre: usuarios/membresías persisten un restart controlado.

## RB16 - Incidente de privacidad

- Señal: PII accesible o exportación no autorizada.
- Primero: alcance, categorías, sujetos, jurisdicción.
- No tocar: no alterar logs/evidencia.
- Contener: revocar acceso, aislar artefacto.
- Recuperar: retirar de exposición y rotar identificadores si aplica.
- Cierre: DPO/legal decide notificación, acciones y retención.

## RB17 - Error en picks/liquidación

- Señal: resultado/ROI discrepa de fuente oficial.
- Primero: congelar grading y guardar fuente/timestamp.
- No tocar: no editar historial sin audit trail.
- Contener: retirar pick/ROI de superficies y Telegram futuro.
- Recuperar: recalcular idempotente con doble revisión.
- Rollback: restaurar settlement previo si nuevo no se valida.
- Cierre: track record y clientes reconciliados.

## RB18 - Error timezone/Madrid

- Señal: partido en día/hora incorrectos.
- Primero: timestamps raw, timezone provider, DST.
- No tocar: no corregir a mano múltiples filas.
- Contener: excluir registros ambiguos.
- Recuperar: conversión canónica UTC -> Europe/Madrid y reprocess.
- Cierre: fixtures invierno/verano/borde de día.

## RB19 - Falso directo

- Señal: live sin marcador, minuto o fase explícita/fresca.
- Primero: evidencia provider/cache/DB.
- No tocar: no relajar gate para conservar conteo.
- Contener: excluir de arrays, KPI, cards, SHARK y Telegram.
- Recuperar: resync; reaparece solo con evidencia válida.
- Cierre: cero falsos y live real aún visible.

## RB20 - Caída total

- Señal: público, auth y health inaccesibles.
- Primero: DNS, Render status, servicio, SHA, DB mount.
- No tocar: DB/secrets/pagos/Telegram sin diagnóstico.
- Contener: IC, freeze deploy, estado externo.
- Recuperar: plataforma -> aplicación -> DB -> auth -> datos -> integraciones.
- Rollback: código si causa release; DB solo si corrupción.
- Cierre: 60 min estable, reconciliación y postmortem P0.

