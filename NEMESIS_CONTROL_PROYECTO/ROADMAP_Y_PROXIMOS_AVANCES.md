# Roadmap y Proximos Avances

Fecha de conciliacion: 2026-09-06 (Europe/Madrid).

La prioridad de desarrollo no equivale a severidad de incidencia. `PUBLICADO`
describe la capacidad existente en `419a04d8`; no certifica por si mismo el
incremento local actual ni cobertura deportiva real.

## Tablero unico

| ID | Estado | Alcance | Responsable | Evidencia | Dependencia | Aceptacion | Siguiente accion |
|---|---|---|---|---|---|---|---|
| NEM-01 | VALIDADO LOCAL | Conservar y conciliar lo ya hecho | Direccion / Release | Sports Truth integrado en `419a04d8`; snapshot selectivo SHA-256 del nuevo incremento fuera del release | Ninguna | Incremento recuperable sin DB, secretos ni workspace completo | Mantener manifiesto hasta decision de publicacion |
| NEM-02 | PUBLICADO | Preparar candidato Sports Truth | Datos deportivos / QA | `MATCH-STATUS-TRUTH-V2` integrado en `419a04d8`; runtime/health alineados read-only | Certificacion deportiva real sigue en curso | Una sola verdad, reloj de proveedor explicito, sin falso LIVE/minuto/score | Continuar observacion real sin reiniciar DAY 3-7 |
| NEM-03 | BLOQUEADO | Publicar y verificar SHA | Release / Operaciones | Local/origin/Render parten de `419a04d8`; Match Context sigue sin commit | Autorizacion explicita de commit/push/deploy | Local == GitHub == Render y Production Sentinel posterior | Revisar y autorizar o rechazar el diff actual |
| NEM-04 | EN DESARROLLO | Disponibilidad deportiva y presupuesto | Datos deportivos | Runtime/master tick read-only: pipeline `PARTIAL`; `/api/live` puede sincronizar y no se uso para observar | Cuota/plan y observacion real | Separar configurado, autenticado, cuota, ultima respuesta, cobertura y frescura | Continuar por DB/cache/logs; disenar contrato read-only de `/api/live` aparte |
| NEM-05 | EN DESARROLLO | Salud honesta, confianza y frescura | Arquitectura / QA | HTTP 200 y job PASS separados de Sports Truth; confianza stale/unknown/conflict limitada localmente | Contrato agregado compatible pendiente | Ningun estado `Alta` con evidencia obsoleta/desconocida/conflictiva | Definir campos agregados sin romper liveness |
| NEM-06 | EN DESARROLLO | Telegram, picks y SHARK sobre el mismo estado | SHARK / Telegram / QA | Master runner PASS; Telegram `OLD_MATCH`; Continuous Evolution `SKIPPED_NOT_DUE`; cero accion iniciada aqui | Pruebas de bloqueo por entidad afectada | Contenido afectado bloqueado sin cerrar todo el producto | Auditar propagacion focal tras publicacion autorizada |
| NEM-07 | VALIDADO LOCAL | Recuperar V944/V946 y documentos congelados | Arquitectura / Producto | V944 en Git; documento original V946 no recuperado; alcance actual establecido expresamente | Fuente original V946 solo para atribucion historica | No deducir fases por numeracion | No llamar V946/PHASE_3_COMPLETE al incremento actual |
| NEM-08 | VALIDADO LOCAL | Match Center y navegacion deportiva | Producto / Datos | `MATCH_CONTEXT_INTELLIGENCE_CONTINUATION`; 19/19 focal, 446/446 suite, Browser 60 capturas y 54/54 clicks | Publicacion autorizada y cobertura real | Contexto factual, exacto por identidad/temporada, sin red ni escrituras en render | Revision del diff y autorizacion separada de publicacion |
| NEM-09 | PUBLICADO | Cliente, movil, admin y membresias | Cliente / Admin / QA | Calendario 4/4; Match 6/6; Founder/Admin autenticado 9/9 en local aislado | No equivale a Browser QA completo de toda la app | Sin fuga cliente/admin ni acciones rotas | Mantener backlog verificable, no redisenar ahora |
| NEM-10 | PROPUESTO | Innovacion `Que ha cambiado` | Producto / SHARK | Requisito conceptual recuperado; no hay evidencia de historial por usuario suficiente | Datos reales, fuente, hora y dedupe | Resumen factual; interpretacion SHARK separada | No implementar en el candidato actual |
| NEM-11 | BLOQUEADO | Comercializacion controlada | Founder / Comercial | Stripe live, Telegram comercial y usuarios reales fuera de autorizacion | Certificaciones externas y aprobacion humana | Sin gasto, cobro, envio o publicacion automatica | Reabrir solo despues de release y gates externos |

## Capacidad funcional de este ciclo

Se completo localmente una sola capacidad:
`MATCH_CONTEXT_INTELLIGENCE_CONTINUATION`. Reutiliza V944, MatchStory, Sports
Knowledge y Sports Truth; anade contexto factual de clasificacion, forma, H2H,
competicion, temporada, jornada y Madrid Time con estados honestos. No se abre
otra capacidad en esta sesion.

## Fuera de alcance

- Rediseno visual global.
- Nuevo motor, proveedor, worker o ruta.
- Descomposicion masiva de `app.py`.
- Purga global de informes, runtime o CSS historico.
- Activar Stripe live, Telegram comercial, gasto o produccion.
