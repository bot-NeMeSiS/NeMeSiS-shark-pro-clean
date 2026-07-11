# V930 Browser QA Comparison

- Estado: `CAPTURED`.
- Playwright/Chromium: disponibles y ejecutados.
- Capturas finales: 198.
- Rutas únicas: 33.
- Perfiles: desktop 1366x768, 1440x900, 1600x900, 1920x1080; móvil 390x844 y 430x932.
- Sesiones: pública, cliente mock seguro y admin mock seguro.
- DB: temporal. Proveedores externos: 0. Telegram/pagos: no ejecutados.
- Errores: 0. Overflow horizontal de documento: 0.
- Comparaciones heurísticas: 198; 192 sin gap estructural y 6 del detalle inexistente pendientes por datos reales.

## Revisión humana aplicada

Se revisaron visualmente home, app, calendario, live, picks, histórico, Telegram, planes, perfil, dashboard admin, Telegram admin, usuarios, pagos, Workforce, Sentinel y Outbox. La segunda ronda corrigió underlap de topbars, navegación admin móvil, iconos genéricos, títulos admin cortados, copy y exposición de ruta local.

Las capturas están en `reports/V930_browser_qa/`; el ZIP excluye PNG pesados. No se declara pixel-perfect: las 16 comparaciones finas deben revisarse humanamente tras desplegar V930.
