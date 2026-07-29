# BETA PROGRAM

Fecha Madrid: 2026-07-29

Objetivo: lanzar una beta controlada que aprenda sin poner en riesgo pagos, datos ni reputacion.

Produccion modificada: false

Commit/push/deploy: no ejecutados

## Executive Summary

- **La beta debe ser el puente entre producto local fuerte y empresa escalable.** NeMeSiS ya tiene mucho producto; ahora necesita evidencia de uso real: activacion, comprension, retencion, soporte, conversion y confianza.
- **La beta no debe empezar con crecimiento masivo.** Debe empezar con 10-25 usuarios, sin prometer beneficios, con pagos controlados/test si Stripe no esta cerrado, y con Telegram limitado.
- **El objetivo principal no es vender mucho: es descubrir que rompe, que confunde y que genera valor diario.**

## Objetivos De Beta

1. Medir si un usuario encuentra un partido rapidamente.
2. Medir si entiende Match/Team/Competition/Player Center.
3. Medir si SHARK aporta claridad real.
4. Medir si favoritos, watchlist y briefing generan retorno.
5. Medir si FREE entiende por que PRO/ELITE tiene valor.
6. Medir soporte, cancelacion y dudas.
7. Detectar errores operativos antes de trafico real.

## Fases

### Fase 0 - Preparacion interna

Duracion: hasta cerrar P1.

Criterios:

- Cron master y sports status documentados.
- Restore drill aislado.
- Stripe test completo.
- Telegram test controlado.
- SLO internos definidos.
- Soporte listo.

### Fase 1 - Beta cerrada manual

Usuarios: 10-25.

Condiciones:

- invitacion manual;
- feedback directo;
- pagos reales desactivados o limitados segun certificacion;
- Telegram solo canal/control autorizado;
- soporte manual;
- comunicacion clara de beta.

### Fase 2 - Beta ampliada

Usuarios: 50-200.

Condiciones:

- sin P1 abiertos;
- metricas de activacion estables;
- restore probado;
- alertas externas activas;
- soporte con tiempos medidos.

### Fase 3 - Release Candidate

Usuarios: 200-1000.

Condiciones:

- Stripe real certificado si se cobra;
- Telegram con limites;
- datos deportivos frescos;
- error budget estable;
- dashboard de negocio.

## Metricas Minimas

| Metrica | Objetivo inicial | Estado |
| --- | ---: | --- |
| Primer partido abierto | >70% | HIPOTESIS |
| Primer SHARK comprendido | >60% | HIPOTESIS |
| Primer favorito/watchlist | >40% | HIPOTESIS |
| Retorno dia siguiente | >30% | HIPOTESIS |
| Interes PRO/ELITE | >15% | HIPOTESIS |
| Quejas por confusion | <20% | HIPOTESIS |
| Incidentes P1 | 0 abiertos | REQUISITO |
| Pagos mal activados | 0 | REQUISITO |
| Telegram duplicado | 0 | REQUISITO |

## Eventos A Medir

- registro completado;
- login;
- primer partido abierto;
- primer centro deportivo abierto;
- primer SHARK abierto;
- favorito creado;
- watchlist creada;
- filtro usado;
- plan visto;
- checkout iniciado;
- checkout completado test/real;
- soporte iniciado;
- cancelacion solicitada;
- error visible;
- retorno dia siguiente.

## Guardrails

- No datos inventados.
- No mensajes de ganancia garantizada.
- No Telegram masivo.
- No pagos reales sin Stripe certificado.
- No fuentes deportivas nuevas sin Gateway approval.
- No experimentos sobre precios, riesgo, stake o privacidad sin aprobacion.
- No automatizar reembolsos.
- No borrar perfiles sin confirmacion.

## Segmentos Beta

| Segmento | Valor |
| --- | --- |
| Usuario deportivo casual | Valida claridad y velocidad. |
| Usuario de picks responsable | Valida SHARK, track record y Telegram. |
| Usuario mobile-first | Valida densidad y navegacion. |
| Usuario admin/operador | Valida Operations Center y soporte. |

## Encuesta Corta

1. Encontraste rapido el partido que buscabas?
2. Entendiste por que ese partido era relevante?
3. SHARK te ayudo o te parecio tecnico?
4. Que abririas cada dia?
5. Que te haria pagar PRO?
6. Que te generaria desconfianza?
7. Que sobraba?
8. Que faltaba?

## Criterios GO/NO-GO

GO a beta ampliada si:

- no hay P1 abiertos;
- usuarios entienden propuesta;
- retencion inicial existe;
- soporte puede responder;
- pagos y Telegram estan certificados segun alcance.

NO-GO si:

- hay confusion mayoritaria sobre SHARK o planes;
- cron/datos siguen PARTIAL sin explicacion;
- restore no probado;
- Stripe/Telegram no cerrados;
- errores P1 se repiten.

## Siguiente Unica Accion

No abrir beta hasta cerrar el drill de operaciones criticas: cron/master tick, restore aislado, Stripe test y Telegram test controlado.
