# PQV939-007 - Browser QA aislado

Fecha Madrid: 2026-07-23

## Alcance

Validación local y read-only de la corrección de presentación de marcas de sincronización. Se usó una instancia Flask aislada, una DB SQLite temporal eliminada al terminar y cuentas de prueba locales. Telegram, Stripe, OpenAI y proveedores deportivos quedaron desactivados; no hubo llamadas externas.

## Perfiles y rutas

- Desktop: `1366x768`.
- Móvil: `390x844`.
- Rutas cliente/públicas: `/`, `/app`, `/calendar`, `/live`, `/picks`, `/match/qa-pqv939-007` y `/shark`.
- Ruta admin relacionada: `/admin/realtime-center`.
- Capturas: 16, una por ruta y perfil.
- Polling validado: `/calendar` en desktop y móvil tras avance controlado del reloj del navegador.

## Resultado

**PASS LOCAL**

- HTTP 200: 16/16.
- Overflow horizontal: 0.
- Errores de consola: 0.
- Errores de página: 0.
- Respuestas 5xx: 0.
- Navegación duplicada: 0.
- Mezcla cliente/admin: 0.
- Controles cortados: 0.
- Literales `None`, `null` o `undefined`: 0.
- Llamadas externas: 0.
- Telegram enviado: no.
- Stripe ejecutado: no.
- OpenAI llamado: no.

## Contrato PQV939-007

- El cliente no muestra ISO crudo en render inicial ni después del polling.
- Cuando la marca secundaria es visible, presenta `22 jul 2026, 14:25 · Madrid`.
- En móvil la marca secundaria puede ocultarse por la densidad responsive existente; el ISO continúa fuera del texto visible y permanece disponible como evidencia de máquina.
- El admin técnico conserva el ISO exacto para diagnóstico.
- El atributo `datetime` y `data-v939-sync-raw` preservan la trazabilidad sin convertirla en copy cliente.
- `/shark` no consume esa barra en el estado probado y no fue modificado.

## Revisión visual humana

- Calendario desktop: etiqueta Madrid legible, alineación estable y sin desbordes.
- Calendario móvil: estado de sincronización comprensible, sin ISO visible, sin solapamiento y con bottom nav intacta.
- Realtime admin: ISO técnico conservado, navegación admin aislada y sin elementos cliente.

## Evidencia

- Resultado estructurado: `browser_qa/V939_P2_PQV939_007/after/browser_qa_result.json`.
- Capturas: `browser_qa/V939_P2_PQV939_007/after/`.

## Limitaciones

- Producción no fue abierta, modificada ni certificada.
- Los datos deportivos usados fueron una fixture temporal completa y claramente identificada para comprobar presentación; no se presentan como datos reales.
- La grabación original solo aporta referencia desktop. La evidencia móvil procede del Browser QA local solicitado.

