# PQV939-006 - Alcance y evidencia

## Problema demostrado

- Prioridad: `P2`.
- Evidencia oficial: Inicio, Partidos, Live, Picks y SHARK; especialmente `00:00`, `02:07` y `02:13` del vídeo maestro.
- Texto observado: referencias visibles a `DB/cache` y `DB y caché durante render`.
- Impacto: el cliente recibe detalles de implementación en lugar de entender disponibilidad, frescura y siguiente acción.

## Causa raíz

El snapshot realtime comparte `safe_message` entre API, macro y polling. Cuando existen partidos o picks, el mensaje se construye como `Datos reales actualizados desde DB/cache`. El macro cliente lo imprime literalmente y el JavaScript vuelve a insertarlo en cada actualización. Live añade un segundo texto técnico fijo en su contrato visual.

No es un problema de datos, API, caché, SHARK, Telegram ni rutas. Es un contrato de copy sin separación suficiente por audiencia.

## Consumidores afectados

- `/`.
- `/app`.
- `/calendar` y aliases equivalentes.
- `/live` y aliases equivalentes.
- `/picks`.

SHARK aparece en la evidencia por el ecosistema de confianza, pero su panel no debe modificarse salvo que el Browser QA reproduzca el término prohibido. Los paneles admin conservan diagnóstico técnico.

## Corrección mínima autorizada

1. Sustituir el mensaje realtime cliente por un resultado comprensible y honesto.
2. Cambiar los fallbacks del macro y del polling para que nunca introduzcan `DB`, `cache` o `render` en cliente.
3. Traducir la fila técnica de Live a disponibilidad para el usuario.
4. Mantener cache, proveedor y render como evidencia operativa admin.
5. Añadir una regla estática de audiencia reutilizada por Sentinel, AutoPilot y Company Intelligence.

## Términos y reglas

- Prohibidos en copy cliente contextual: `DB`, `DB/cache`, `caché durante render`, `render cache-only` y equivalentes de implementación.
- Permitidos cuando aportan trazabilidad real: nombre del proveedor, fuente registrada, última actualización, frescura, lectura retrasada y datos excluidos.
- Permitidos en admin: DB, caché, render, TTL, polling y diagnóstico de proveedor.

## Fuera de alcance


- `PQV939-007` y posteriores.
- Rediseño, CSS, rutas, arquitectura o motores nuevos.
- Datos deportivos, SHARK, Telegram, Stripe, DB real y proveedores.
- Cambiar la API pública más allá del mensaje seguro ya consumido por cliente.
- Implementar Sports Experience.

## Criterio de aceptación

- Las cinco pantallas no muestran términos técnicos prohibidos en render inicial ni tras polling.
- La información sobre datos reales, retrasados o ausentes sigue siendo honesta.
- Admin conserva su diagnóstico técnico.
- Desktop y móvil sin overflow, errores de consola ni regresión funcional.
- Sentinel abre P2 si reaparece el contrato roto.
- AutoPilot propone una corrección con aprobación humana y no la autoaplica.
- Producción permanece intacta.

## Cierre local

- Estado: `RESUELTO LOCALMENTE`.
- Snapshot normal y fallback de excepción: copy cliente seguro.
- Macro y polling: separación explícita cliente/admin.
- Live: disponibilidad explicada sin internals.
- SHARK: sin términos prohibidos visibles; no se modificó.
- Browser QA: 12/12 PASS, 10 polls, 0 overflow, 0 consola, 0 errores 5xx y 0 llamadas externas.
- Pruebas focalizadas P1/P2: 23/23 PASS.
- Sentinel y AutoPilot: regresión P2 reproducida, tarea con aprobación humana y cero acciones peligrosas.
- Evidencia: `reports/PQV939_006_BROWSER_QA.md`.
- Producción, push y deploy: no realizados.
