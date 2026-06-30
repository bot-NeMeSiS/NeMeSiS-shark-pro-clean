# V871 Sentinel Visible UI and Empty Space Rules QA

## Actualizado
- Sentinel revisa texto interactivo de botones y CTAs.
- Se evita marcar filas completas de partido como botones.
- Se mantiene detección de copy técnico visible, mojibake y frases irresponsables.

## Resultado local
- `run_continuous_sentinel_static.py` alcanzó score 10.0 con 0 incidencias abiertas tras el ajuste.
- Durante la pasada final detectó mojibake real en `/support`, `/partidos` y `/calendar`; se corrigió normalizando cadenas visibles heredadas y reparando marcadores internos de QA.

## Alcance
La detección de huecos extremos es estática y heurística. La confirmación fina requiere navegador/capturas reales.
