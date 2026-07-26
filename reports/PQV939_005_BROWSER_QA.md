# PQV939-005 Browser QA

## Alcance

- Incidencia: `PQV939-005`.
- Defecto: iconos de las reglas de confianza renderizados como cajas vacias.
- Entorno: local, aislado y sin servicios externos.
- DB: fixture temporal de QA fuera del release; la DB real no se leyo ni modifico.
- Produccion, GitHub, Telegram y Stripe: no modificados.

## Matriz ejecutada

| Perfil | Resolucion | Rutas |
|---|---:|---|
| Desktop | 1366x768 | `/app`, `/picks`, `/shark`, `/match/pqv939005-match`, `/track-record` |
| Movil | 390x844 | `/app`, `/picks`, `/shark`, `/match/pqv939005-match`, `/track-record` |

## Resultado

- Casos: `10/10 PASS`.
- HTTP 200: `10/10`.
- Overflow horizontal: `0`.
- Errores de consola: `0`.
- Errores de pagina: `0`.
- Intentos externos: `0`.
- Respuestas fallidas: `0`.
- Errores 500 o traceback en el servidor local: `0`.
- Fallos del contrato de iconos: `0`.

En cada panel visible, los tres iconos contienen SVG, son visibles, conservan fondo transparente y no heredan padding ni borde del chip. Los textos permanecen contenidos en desktop y movil. En `/track-record` el panel no aparece sin una muestra evaluable, que es el comportamiento seguro esperado; la ruta sigue en 200 y sin overflow.

## Comparacion con la evidencia oficial

El video oficial mostraba un rectangulo vacio antes de `Picks completos`, `Historico evaluable` y `Sin beneficio garantizado`. Las capturas posteriores muestran los tres pictogramas visibles dentro de sus chips, sin caja interna ni deformacion. El defecto descrito ya no se reproduce en los mismos consumidores funcionales.

## Evidencia

- Resultado estructurado: `browser_qa/V939_P2_PQV939_005/after/browser_qa_result.json`.
- Close-up desktop: `browser_qa/V939_P2_PQV939_005/after/desktop_1366x768_trust-panel.png`.
- Close-up movil: `browser_qa/V939_P2_PQV939_005/after/mobile_390x844_trust-panel.png`.
- Capturas completas: cinco rutas en cada viewport dentro de `browser_qa/V939_P2_PQV939_005/after/`.

## Limitaciones

El navegador integrado no pudo iniciarse por un fallo local del sandbox de Windows al aplicar ACL. Se uso el Playwright local ya disponible, con inspeccion DOM, estilos computados, consola, red y capturas. No se certifica produccion ni se usa este fixture como evidencia de datos deportivos reales.

## Decision

`PQV939-005`: **RESUELTO LOCALMENTE**. La evidencia visual y automatizada confirma que el video original ya no mostraria este defecto en el estado equivalente.
