# NeMeSiS SHARK PRO - Plan de respuesta a incidentes

## Principios

1. Proteger personas, datos y dinero antes que disponibilidad.
2. No restaurar, borrar, cobrar, enviar o rotar sin autorización correspondiente.
3. Preservar evidencia y timestamps Madrid/UTC.
4. No declarar recuperación hasta validar cliente, admin, datos y dependencias afectadas.
5. Un incidente P0/P1 tiene un Incident Commander único.

## Severidad y objetivos

| Nivel | Ejemplo | Confirmación | Actualización | Objetivo contención |
|---|---|---:|---:|---:|
| P0 | Pérdida/PII/secreto/cobro/falso dato masivo | 5 min | 15 min | 15 min |
| P1 | Login, feed, pago, Telegram o función crítica | 10 min | 30 min | 30 min |
| P2 | Degradación con fallback | 30 min | 2 h | 4 h |
| P3 | Visual/menor | 1 día | Al cierre | Siguiente release |
| P4 | Preventivo | Backlog | Semanal | Planificado |

## Ciclo profesional

1. **Detectar:** alerta, usuario, proveedor o auditoría.
2. **Confirmar:** reproducir con lectura segura; descartar falso positivo.
3. **Clasificar:** severidad, alcance, datos, dinero, privacidad.
4. **Contener:** kill switch, modo seguro, pausa o rollback de código.
5. **Comunicar:** interno primero; cliente solo con hechos confirmados.
6. **Corregir:** cambio mínimo, branch/commit trazable, test de regresión.
7. **Validar:** local, CI, canary/Render, rutas afectadas y no regresión.
8. **Recuperar:** reactivar gradualmente; no reponer colas sin dedupe.
9. **Monitorizar:** 15/60 min y 24 h según severidad.
10. **Cerrar:** criterios medibles satisfechos.
11. **Documentar:** timeline, causa, impacto, decisiones y evidencia.
12. **Prevenir:** owner, fecha y control que reduzca recurrencia.

## Registro mínimo

- ID y severidad.
- Inicio, detección, contención, recuperación y cierre en Madrid y UTC.
- Runtime/SHA y entorno.
- Síntoma, alcance y clientes afectados.
- Datos, dinero, privacidad y legal.
- Logs redactados; nunca secretos/cookies/PII.
- Acciones ejecutadas, autor y aprobación.
- Backup/rollback usados.
- Evidencia de cierre y test añadido.

## Autoridad

| Acción | Autoridad mínima |
|---|---|
| Activar estado seguro o pausar polling | Operaciones según runbook |
| Pausar Telegram/cron | Incident Commander + owner de integración |
| Rollback de código | Release Manager + Incident Commander |
| Rotar secreto | Security + propietario del sistema |
| Restaurar DB | DB Lead + Incident Commander + segunda aprobación |
| Reembolsar/cobrar | Payments + Dirección; nunca automático |
| Notificación legal/privacidad | Dirección + DPO/asesoría legal |
| Reabrir producción de pago | GO explícito del comité |

## Comunicación

### Interna

Formato: “P1 Datos stale | inicio 14:10 | impacto: live/picks | contención: arrays públicos vacíos | próxima actualización 14:40”.

### Cliente

- Confirmar solo lo sabido.
- Explicar impacto y alternativa.
- No culpar al proveedor ni prometer hora sin evidencia.
- Para datos: “La actualización deportiva está temporalmente detenida; no mostramos información no verificada”.
- Para pagos: confirmar que no se duplicarán cargos mientras se reconcilia.

## Postmortem

Obligatorio para P0/P1, sin culpa personal. Debe responder:

- Qué cambió.
- Por qué los controles no evitaron/detectaron antes.
- Qué decisión fue correcta/incorrecta.
- Qué señales faltaban.
- Una acción preventiva con owner/fecha/test.

## Criterios de cierre

- Causa raíz identificada o hipótesis acotada con plan.
- Contención retirada de forma controlada.
- SLO cumplido durante ventana de observación.
- Datos/membresías/pagos reconciliados.
- Sin 5xx nuevos relacionados.
- Sentinel y monitor externo verdes.
- Evidencia almacenada sin PII/secrets.

