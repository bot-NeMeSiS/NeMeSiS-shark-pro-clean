# V862 Sentinel Browser QA Optional Notes

## Modo estático

`tools/run_continuous_sentinel_static.py` funciona siempre con Flask test client y no requiere navegador.

## Modo browser futuro

Playwright/browser queda como posibilidad futura. Si no está instalado, el sistema debe reportar `browser visual QA not available locally` y no fallar.

## Honestidad

No se declara pixel-perfect ni navegador real si no se ejecuta browser mode con capturas reales.
