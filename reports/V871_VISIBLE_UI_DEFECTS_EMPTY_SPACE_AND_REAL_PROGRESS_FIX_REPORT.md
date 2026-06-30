# V871 Visible UI Defects, Empty Space Screen by Screen PRO MAX

V871 corrige defectos visibles que los checks anteriores no reflejaban suficientemente: copy duplicado, CTAs repetidos, mojibake, JS de interacción roto, exceso de aire visual en cliente/admin y brecha pantalla por pantalla frente a la referencia.

## Corregido
- Versionado exacto V871 PRO MAX aplicado en `VERSION.txt`, `APP_VERSION`, `app.py`, `base.html` y cache CSS.
- Runtime añade `has_v871_visible_ui_empty_space_screen_fix`.
- CSS V871 añade una capa compacta y ordenada para densidad visual.
- Sentinel ya distingue botones/CTAs reales de filas completas de partidos.
- Se mantiene el arreglo previo de botones duplicados y texto Telegram.
- Se generaron capturas locales de desktop/móvil y métricas sin scroll horizontal.
- Se normalizó mojibake heredado en cadenas visibles y marcadores internos de QA para que Sentinel vuelva a score 10.0.

## Sin inventar datos
Las mejoras de densidad usan estados seguros y estructura visual; no añaden partidos, picks, cuotas, resultados ni métricas falsas.
