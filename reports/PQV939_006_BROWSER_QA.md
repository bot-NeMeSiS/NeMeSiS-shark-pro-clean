# PQV939-006 - Browser QA

## Alcance

Validación local y aislada del contrato de copy cliente de realtime. No se tocó producción, GitHub, la DB real, Telegram, Stripe ni proveedores deportivos.

Rutas:

- `/`.
- `/app` con cuenta local temporal.
- `/calendar` con cuenta local temporal.
- `/live` con cuenta local temporal.
- `/picks` con cuenta local temporal.
- `/shark` con cuenta local temporal.

Perfiles:

- Desktop `1366x768`.
- Móvil `390x844`.

## Entorno seguro

- Chromium local mediante Playwright.
- SQLite temporal fuera del release.
- Usuario de QA temporal sin datos personales reales.
- Proveedores, OpenAI, Telegram, pagos y jobs de background desactivados.
- Service worker bloqueado para leer los assets locales actuales.
- Servidor local terminado al finalizar.

## Validación del polling

El componente impone un mínimo real de 30 segundos. El QA usó el reloj virtual de Playwright para avanzar 33 segundos después de emitir `v934:refresh`, ejecutando el JavaScript real sin alterar el producto.

- Barras cliente detectadas: 10.
- Consultas a `/api/realtime/sports`: 10.
- Barras con modo técnico cliente: 0.
- Términos prohibidos antes del polling: 0.
- Términos prohibidos después del polling: 0.

Términos comprobados: `DB/cache`, `DB y caché durante render`, claves de proveedor, llamadas al proveedor y equivalentes de implementación.

## Resultado

| Control | Resultado |
|---|---:|
| Casos de ruta | 12/12 PASS |
| HTTP 200 | 12/12 |
| Overflow horizontal | 0 |
| Errores de consola | 0 |
| Errores de página | 0 |
| Respuestas 5xx | 0 |
| Peticiones externas del navegador | 0 |
| `None`, `null` o `undefined` visibles | 0 |
| Servidor local cerrado | Sí |

El estado vacío mostrado fue honesto: `Esperando una sincronización real; no se muestran datos de ejemplo.` El mismo mensaje seguro permaneció después del polling. SHARK no mostró términos técnicos; su contexto interno de proveedor no se renderiza en la plantilla cliente.

El fallback de excepción se validó además con una prueba de regresión aislada: conserva la última información confirmada sin mencionar caché o render.

## Evidencia

- Capturas: `browser_qa/V939_P2_PQV939_006/after/`.
- Resultado estructurado y logs: área local de visualización `V939_P2_PQV939_006` fuera del release.
- Pruebas: `tests/test_v939_product_perfection_p2.py`.

## Gate

`PQV939-006_BROWSER_QA = PASS_LOCAL`

No certifica producción ni pixel-perfect. La comparación es contra el defecto textual demostrado en el vídeo maestro; una revisión humana de las capturas sigue siendo el último control visual subjetivo.
