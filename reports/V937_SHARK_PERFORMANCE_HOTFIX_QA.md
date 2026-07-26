# V937 SHARK Performance Hotfix QA

## Alcance

- Base y rollback: `261213048fe3f92a58488b1119092922cdfc5db5`.
- Rama: `hotfix/v937-shark-performance`.
- Versión conservada: `V937_PRODUCT_PERFECTION_FULL_ECOSYSTEM_LAUNCH_CLOSEOUT_FINAL`.
- Sin cambios de diseño, datos deportivos, Stripe, Telegram, DB real o versión.

## Causa raíz

`GET /shark` construía el dashboard cliente completo aunque la plantilla solo necesitaba el resumen deportivo compacto. Después volvía a calcular el briefing y el contexto SHARK, repetía el diagnóstico del proveedor y llamaba a `shark_answer()`, que reconstruía el contexto y escribía memoria SHARK durante una petición GET.

El resultado eran 138 lecturas de alto nivel y una escritura por carga. En Render, la latencia de I/O multiplicaba ese trabajo hasta 6,3-8,7 segundos; una medición directa observó 10,174 s totales y 8,715 s de backend.

Browser QA descubrió además una expresión regular JavaScript mal cerrada en el guard de `/shark`. Se sustituyó por una comparación de ruta equivalente y se añadió su regresión.

## Corrección mínima

- Contexto deportivo compacto y cache-only ya existente.
- Briefing, estado de proveedor y contexto SHARK construidos una sola vez por petición.
- Respuesta de página generada con la función pura existente, sin escribir memoria en GET.
- Estado del proveedor reutilizado con las mismas etiquetas y mensajes previos.
- `Server-Timing` por fase y cabeceras seguras de origen/cache.
- Sin caché privada global nueva y sin llamadas externas durante render.

## Benchmark reproducible

Misma máquina, misma copia temporal de DB, diez ejecuciones por versión y OpenAI desactivado.

| Métrica | Base `2612130` | Hotfix |
| --- | ---: | ---: |
| Cold cache | 92,1 ms | 90,7 ms |
| Hot cache mediana | 76,2 ms | 32,5 ms |
| Mediana total | 76,3 ms | 33,2 ms |
| p95 | 110,5 ms | 39,5 ms |
| Mínimo | 68,9 ms | 28,7 ms |
| Máximo | 111,9 ms | 90,7 ms |
| Lecturas por carga | 138 | 6 |
| Llamadas externas | 0 | 0 |
| Escrituras SHARK en 10 GET | 10 | 0 |
| Respuesta | 44.606 bytes | 44.606 bytes |

La prueba de gate final obtuvo 78,6 ms cold, 25,0 ms de mediana hot, p95 de 27,3 ms, fallback de proveedor en 29,1 ms y DB vacía en 157,6 ms. Todos quedan muy por debajo de los presupuestos de 4 s, 1,5 s y 2,5 s.

Fases observadas en caliente: sports context 16,9 ms, briefing 4,7 ms, assistant context 0,3 ms, answer 0,1 ms y Jinja 1,4 ms.

## Browser QA reducido

- 10 capturas: Home, Calendar, Live, Picks y SHARK.
- Desktop: 1440x900.
- Móvil: 390x844.
- HTTP 200: 10/10.
- Overflow: 0.
- Errores JavaScript/consola: 0.
- Internal Error visible: 0.
- SHARK final: 67,1 ms desktop y 34,9 ms móvil de backend en las capturas finales.
- Evidencia: `reports/browser_qa_v937_shark_hotfix/`.

## Regresiones

Pasaron compilación, Jinja V937, Madrid Time, checks V929-V934, V936, V937 Product Update y Sports Lifecycle, SQLite legacy/bloqueada, SHARK fallback/no hallucination/membership/match/pick, sports value, realtime, odds freshness, match lifecycle, smoke de 58 rutas, 664 rutas de navegación, 929 enlaces, Sentinel 10/10, 0 incidencias y Secret Guard equivalente sobre 2.272 archivos con 0 hallazgos.

Avisos de base no causados por el diff:

- V935 Pick Lifecycle contiene `PUBLISHED` duplicado en su lista estática.
- V937 Operational Closeout conserva una expectativa previa sobre un live retrasado.
- El check V929 de separación busca clases antiguas, mientras Browser QA y Navigation Integrity verifican separación real.
- V729 y V749B tienen allowlists de versión históricas que no incluyen V937.
- `automation_workforce/security_secret_guard.py` no existe en `main`; para la comprobación se ejecutó de forma aislada el guard ya validado del commit `4dd9caa`, sin incorporarlo al hotfix.

## Gate

- SHARK PERFORMANCE GATE local: **PASS**.
- Producción: pendiente de revisión humana, merge normal y certificación Render.
- Cron: no modificado; permanece **PARTIAL** hasta completar primero la certificación SHARK.
- Rollback: `261213048fe3f92a58488b1119092922cdfc5db5`.
