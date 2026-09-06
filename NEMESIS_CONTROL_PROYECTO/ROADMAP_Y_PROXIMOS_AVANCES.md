# Roadmap y Proximos Avances

Fecha de conciliacion: 2026-09-05 (Europe/Madrid).

La prioridad de desarrollo no equivale a severidad de incidencia. `PUBLICADO`
describe la capacidad existente en `fddbeea3`; no certifica por si mismo el diff
local ni cobertura deportiva real.

## Tablero unico

| ID | Estado | Alcance | Responsable | Evidencia | Dependencia | Aceptacion | Siguiente accion |
|---|---|---|---|---|---|---|---|
| NEM-01 | VALIDADO LOCAL | Conservar y conciliar lo ya hecho | Direccion / Release | Copia exacta, patch y SHA-256 fuera del release; Git sin operaciones destructivas | Ninguna | Candidato recuperable sin DB, secretos ni workspace completo | Mantener manifiesto hasta decision de publicacion |
| NEM-02 | VALIDADO LOCAL | Preparar candidato Sports Truth | Datos deportivos / QA | `MATCH-STATUS-TRUTH-V2`; 27/27 focales, 118/118 matriz y 427/427 suite | Revision Founder antes de publicar | Una sola verdad, reloj de proveedor explicito, sin falso LIVE/minuto/score | Revisar diff y autorizar o rechazar candidato |
| NEM-03 | BLOQUEADO | Publicar y verificar SHA | Release / Operaciones | Local y `origin/main` parten de `fddbeea3`; cambios siguen sin commit | Autorizacion explicita de commit/push/deploy | Local == GitHub == Render y Production Sentinel posterior | No ejecutar durante este encargo |
| NEM-04 | EN DESARROLLO | Disponibilidad deportiva y presupuesto | Datos deportivos | Runtime/master tick read-only: pipeline `PARTIAL`; `/api/live` puede sincronizar y no se uso para observar | Cuota/plan y observacion real | Separar configurado, autenticado, cuota, ultima respuesta, cobertura y frescura | Continuar por DB/cache/logs; disenar contrato read-only de `/api/live` aparte |
| NEM-05 | EN DESARROLLO | Salud honesta, confianza y frescura | Arquitectura / QA | HTTP 200 y job PASS separados de Sports Truth; confianza stale/unknown/conflict limitada localmente | Contrato agregado compatible pendiente | Ningun estado `Alta` con evidencia obsoleta/desconocida/conflictiva | Definir campos agregados sin romper liveness |
| NEM-06 | EN DESARROLLO | Telegram, picks y SHARK sobre el mismo estado | SHARK / Telegram / QA | Master runner PASS; Telegram `OLD_MATCH`; Continuous Evolution `SKIPPED_NOT_DUE`; cero accion iniciada aqui | Pruebas de bloqueo por entidad afectada | Contenido afectado bloqueado sin cerrar todo el producto | Auditar propagacion focal tras publicacion autorizada |
| NEM-07 | VALIDADO LOCAL | Recuperar V944/V946 y documentos congelados | Arquitectura / Producto | V944 en Git desde `b6fc366d`; V946 sin ocurrencias en arbol u objetos Git | Prompt/documento original V946 | No deducir alcance por numeracion | Mantener V946 bloqueada hasta recuperar una fuente original |
| NEM-08 | PUBLICADO | Match Center y navegacion deportiva | Producto / Datos | V944 Foundation y ampliaciones posteriores presentes en `main` | Cobertura real e IDs reales | MatchContext puro, rutas reales y fallbacks honestos | No abrir incremento nuevo sin requisito aprobado recuperado |
| NEM-09 | PUBLICADO | Cliente, movil, admin y membresias | Cliente / Admin / QA | Calendario 4/4; Match 6/6; Founder/Admin autenticado 9/9 en local aislado | No equivale a Browser QA completo de toda la app | Sin fuga cliente/admin ni acciones rotas | Mantener backlog verificable, no redisenar ahora |
| NEM-10 | PROPUESTO | Innovacion `Que ha cambiado` | Producto / SHARK | Requisito conceptual recuperado; no hay evidencia de historial por usuario suficiente | Datos reales, fuente, hora y dedupe | Resumen factual; interpretacion SHARK separada | No implementar en el candidato actual |
| NEM-11 | BLOQUEADO | Comercializacion controlada | Founder / Comercial | Stripe live, Telegram comercial y usuarios reales fuera de autorizacion | Certificaciones externas y aprobacion humana | Sin gasto, cobro, envio o publicacion automatica | Reabrir solo despues de release y gates externos |

## Siguiente capacidad funcional

No se abre una segunda capacidad en este ciclo. V944 y sus ampliaciones ya existen;
V946 no tiene especificacion recuperable y los documentos congelados impiden
inventar un nuevo alcance. El unico trabajo funcional del candidato es el
endurecimiento acotado de Sports Truth y sus pruebas.

## Fuera de alcance

- Rediseno visual global.
- Nuevo motor, proveedor, worker o ruta.
- Descomposicion masiva de `app.py`.
- Purga global de informes, runtime o CSS historico.
- Activar Stripe live, Telegram comercial, gasto o produccion.
