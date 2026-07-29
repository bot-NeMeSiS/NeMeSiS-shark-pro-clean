# COMMERCIAL RELEASE PLAN

Fecha Madrid: 2026-07-29  
Objetivo: llevar NeMeSiS SHARK PRO a Release 1.0 comercial sin construir modulos nuevos  
Produccion modificada: false

## Executive Summary

- **El plan recomendado es beta cerrada antes de lanzamiento publico.** La plataforma esta lista localmente, pero el mercado necesita evidencia de pago, soporte, Telegram, conversion y confianza.
- **No se recomienda construir mas producto ahora.** El foco debe ser cerrar gates, medir valor y preparar operacion comercial.
- **La promesa comercial debe ser responsable.** NeMeSiS no vende garantia de acierto; vende contexto, evidencia, seguimiento y ahorro de tiempo.

## Posicionamiento Release 1.0

NeMeSiS SHARK PRO es una plataforma deportiva premium para entender partidos, equipos, competiciones, jugadores y picks con evidencia trazable, SHARK contextual, seguimiento personalizado y Telegram responsable.

No debe posicionarse como:

- App de marcadores generica.
- Bot de apuestas.
- Promesa de ganancias.
- IA que adivina resultados.
- Canal de spam.

## Paquetes Comerciales

| Plan | Trabajo antes de launch | Mensaje correcto |
|---|---|---|
| FREE | Demostrar valor en primer partido y favoritos | Sigue partidos y entiende contexto basico |
| PRO | Certificar picks, Telegram y SHARK contextual | Ahorra tiempo con seguimiento premium responsable |
| ELITE | Certificar profundidad, track record y bankroll responsable | Mayor profundidad y control, no promesa de beneficio |

## Roadmap De Cierre

### Semana 1: Cerrar operacion critica

1. Cron/master tick.
2. Restore aislado.
3. Stripe test.
4. Telegram test.
5. Copy tecnico visible en cliente.

### Semana 2: Preparar beta cerrada

1. Definir 10-25 usuarios beta.
2. Medir primer partido, primer SHARK, primer favorito y primer retorno.
3. Medir intencion de upgrade.
4. Definir soporte manual.
5. Validar mensajes de juego responsable.

### Semana 3: Medir valor y conversion

1. Analizar activacion.
2. Analizar retencion diaria/semanal.
3. Revisar preguntas frecuentes reales.
4. Ajustar copy comercial sin cambiar motores.
5. Validar si PRO/ELITE se entiende.

### Semana 4: Decision de lanzamiento

1. Repetir produccion + QA completa.
2. Revisar riesgos P1.
3. Decidir GO publico, beta ampliada o HOLD.

## Metricas Minimas De Beta

| Metrica | Objetivo inicial | Uso |
|---|---|---|
| Primer partido abierto | >70% de usuarios beta | Activacion |
| Primer SHARK entendido | >60% declara comprenderlo | Valor diferencial |
| Primer favorito | >40% | Retencion |
| Retorno dia siguiente | >30% | Habito |
| Interes PRO | >15% | Senal comercial |
| Quejas por confusion | <20% | Claridad |
| Incidentes P1 | 0 abiertos | Seguridad de launch |

Estos objetivos son hipotesis iniciales, no datos reales.

## Materiales Necesarios

- Pagina o bloque de metodologia.
- Copy de planes FREE/PRO/ELITE.
- Politica de cancelacion/reembolso.
- Mensaje de juego responsable.
- Canal de soporte.
- Checklist de pago y Telegram.
- Runbook de incidente de lanzamiento.

## Criterio GO / NO-GO

GO publico solo si:

- Produccion sigue alineada.
- Cron no esta en PARTIAL.
- Stripe test pasa completo.
- Telegram test pasa completo.
- Restore aislado pasa.
- Browser QA y Sentinel siguen PASS.
- Beta demuestra comprension del valor.
- Soporte y cancelacion estan claros.

NO-GO si:

- Hay P1 abierto.
- Hay pagos no certificados.
- Hay Telegram no controlado.
- Hay datos stale sin explicacion.
- Hay confusion mayoritaria sobre SHARK o planes.

## Siguiente Unica Accion

Cerrar el gate de cron/observabilidad: resolver `v937_sports_cron_status=PARTIAL` y `v937_cron_master_status=NOT_RECORDED`, o documentar oficialmente por que no bloquea la beta.
