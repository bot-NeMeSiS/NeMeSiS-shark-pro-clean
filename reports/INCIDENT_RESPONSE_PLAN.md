# INCIDENT RESPONSE PLAN

Fecha Madrid: 2026-07-29

Alcance: respuesta profesional a incidentes de NeMeSiS SHARK PRO.

Produccion modificada: false

Commit/push/deploy: no ejecutados

## Executive Summary

- **NeMeSiS debe tratar cada fallo como una decision operativa trazable.** Detectar no basta: hay que confirmar, clasificar, contener, comunicar, corregir, validar y cerrar con evidencia.
- **Los incidentes mas graves son datos, pagos, privacidad y disponibilidad.** Un error visual molesta; un pago no activado, secreto expuesto, DB corrupta o Telegram incorrecto puede danar la empresa.
- **La automatizacion puede abrir tareas y recopilar evidencia, pero no debe ejecutar acciones peligrosas sin humano.** Rollback, restore, pagos, Telegram real, cambio de permisos y deploy requieren autorizacion.

## Severidades

| Severidad | Definicion | Ejemplos | Tiempo objetivo |
| --- | --- | --- | --- |
| P0 | Caida total, perdida de datos, secreto expuesto, cobro incorrecto | DB corrupta, token filtrado, cobro real duplicado | Respuesta inmediata |
| P1 | Funcion critica rota para muchos usuarios o riesgo comercial alto | Stripe webhook falla, cron no registra, Telegram duplica | <1h |
| P2 | Degradacion importante con alternativa | p95 alto, stale odds, UX rota en movil | <24h |
| P3 | Problema menor o visual | copy, spacing, empty state | planificado |

## Ciclo De Incidente

1. Detectar.
2. Confirmar.
3. Clasificar severidad.
4. Contener dano.
5. Comunicar internamente.
6. Corregir con minimo cambio.
7. Validar con evidencia.
8. Recuperar servicio.
9. Monitorizar ventana posterior.
10. Cerrar.
11. Documentar causa raiz.
12. Crear prevencion.

## Matriz De Responsabilidad

| Area | Owner primario | Backup necesario |
| --- | --- | --- |
| Disponibilidad Render | Ops Lead | CTO |
| DB/backups | CTO | Ops Lead |
| Datos deportivos | Data Lead | CTO |
| Stripe | Owner + Security Lead | Support Lead |
| Telegram | Ops Lead | Owner |
| Seguridad/privacidad | Security Lead | CTO |
| UX/regresiones | QA Lead | Product Lead |
| Comunicacion cliente | Owner | Support Lead |

## Runbooks Principales

### Render 502/503

- Senal: health falla, 5xx aumenta o usuarios no cargan.
- Primera comprobacion: `/api/health`, `/api/runtime-version`, logs Render read-only.
- No tocar: secretos, DB, deploy sin decision.
- Contencion: pausar cambios, comunicar degradacion si afecta usuarios.
- Recuperacion: rollback solo si SHA nuevo coincide con inicio del fallo.
- Cierre: health estable, p95 normal y Sentinel sin issues.

### Deploy defectuoso

- Senal: runtime SHA nuevo con errores 5xx o rutas rotas.
- Primera comprobacion: diff del commit, route audit, runtime.
- Contencion: detener siguientes deploys.
- Recuperacion: rollback a SHA anterior estable con backup documentado.
- Cierre: Render sirve SHA correcto y QA critica PASS.

### DB bloqueada

- Senal: errores `database is locked`, latencia alta, cron PARTIAL.
- Primera comprobacion: logs, write paths recientes, cron overlap.
- No tocar: no borrar DB, no reiniciar persistencia sin backup.
- Contencion: pausar jobs no criticos.
- Recuperacion: terminar proceso bloqueante, crear backup, validar quick_check.
- Cierre: sin locks sostenidos y rutas criticas PASS.

### DB corrupta

- Senal: quick_check falla, health DB error, datos incoherentes.
- Primera comprobacion: modo read-only, checksum de backup, tamano DB.
- Contencion: poner modo mantenimiento si usuarios afectados.
- Recuperacion: restore desde backup probado, nunca sin copia previa.
- Cierre: quick_check ok, tablas clave y usuarios validados.

### Telegram incorrecto

- Senal: duplicado, destino erroneo, mensaje incorrecto o spam.
- Contencion: desactivar envio real.
- No tocar: no enviar correccion masiva automatica.
- Recuperacion: validar queue/dedupe, preparar comunicado humano si procede.
- Cierre: dry-run PASS, limites activos, evidencia de destino.

### Stripe/webhook fallido

- Senal: pago test/real sin membresia, webhook 4xx/5xx, duplicado.
- Contencion: pausar ventas reales si afecta activacion.
- No tocar: no modificar pagos reales sin evidencia.
- Recuperacion: revisar evento Stripe, idempotency, membresia.
- Cierre: flujo checkout -> webhook -> activacion -> cancelacion test PASS.

### Datos deportivos stale o falsos live

- Senal: last sync viejo, stale odds, live inconsistente.
- Contencion: ocultar o marcar datos no confiables; no generar picks.
- Recuperacion: ejecutar sync autorizado o fallback de cache honesto.
- Cierre: frescura dentro de politica, false-live 0.

### Secreto expuesto

- Senal: Secret Guard, logs, informe o repositorio muestra token.
- Contencion: detener deploy/push, revocar secreto en proveedor.
- Recuperacion: rotar, limpiar historial solo con protocolo autorizado, revalidar.
- Cierre: Secret Guard PASS y proveedor confirma rotacion.

## Acciones Automaticas Permitidas

- Crear incidente interno.
- Recopilar evidencia read-only.
- Ejecutar health checks.
- Ejecutar Sentinel/route audit.
- Generar prompt de correccion.
- Marcar severidad preliminar.

## Acciones Que Requieren Humano

- Deploy.
- Rollback.
- Restore.
- Enviar Telegram real.
- Cobros, reembolsos o cambios de membresia.
- Modificar secretos.
- Cambiar proveedores de datos.
- Desactivar seguridad.

## Evidencia De Cierre

Cada incidente debe cerrar con:

- hora Madrid;
- SHA afectado;
- rutas afectadas;
- usuarios o datos afectados;
- causa raiz;
- accion tomada;
- QA ejecutada;
- rollback o no rollback;
- prevencion futura;
- owner que aprueba cierre.

## Siguiente Unica Accion

Crear una plantilla unica de incidente P0/P1 y usarla en Operations Center, Company Board y Sentinel para que todo fallo tenga el mismo ciclo de vida.
