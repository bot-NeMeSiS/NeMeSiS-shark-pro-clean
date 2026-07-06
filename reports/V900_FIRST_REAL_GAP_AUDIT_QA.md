# V900 First Real Gap Audit QA

## Resultado del worker

`tools/run_reference_visual_gap_scan.py --dry-run` devuelve:

- `reference_count`: 16
- `manifest_count`: 16
- `browser_available`: false
- `gap_count`: 13

## Gaps mas importantes

- Cliente `/app`: debe acercarse a dashboard premium con KPIs, ruta recomendada, partidos destacados, pick destacado y accesos rapidos.
- Movil `/app`: debe acercarse a app nativa compacta con bottom nav clara y cards densas.
- Admin `/admin/dashboard`: debe acercarse a command center con KPIs, grafico, Telegram, lanzamiento, actividad reciente y acciones rapidas.
- Picks `/picks`: debe parecer producto de pago con pick destacado, cuota, riesgo, confianza, stake y motivos.
- Live `/live`: debe parecer marcador premium con estados, minuto, score, escudos y acciones.
- Calendar `/calendar`: debe ser denso, filtrable y claro por competicion/dia.
- Telegram `/telegram`: debe transmitir canal premium, conexion, beneficios y CTA claros.
- SHARK `/shark` y match detail: debe mostrar cerebro SHARK, confianza, datos clave, pick recomendado y forma reciente.
- Membresias `/membresias`: planes FREE/PRO/ELITE claramente diferenciados.
- Profile `/profile`: plan, Telegram, renovacion, favoritos, actividad y seguridad.
- Track record `/track-record`: resultados reales, tablas y transparencia sin inventar ROI.

## Limitacion

Sin Playwright, la comparacion sigue siendo heuristica y basada en referencias importadas, no en capturas reales de la app renderizada.
