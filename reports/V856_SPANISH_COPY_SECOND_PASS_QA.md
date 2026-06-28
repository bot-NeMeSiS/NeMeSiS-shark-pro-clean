# V856 Español y Copy Segunda Pasada

## Criterio
Cliente en español claro, comercial y responsable. Admin puede ser técnico, pero explicado. SHARK y Telegram sin promesas irresponsables.

## Tokens vigilados
- Mojibake: `Ã`, `Â`, `�`, `Ãƒ`, `Ã‚`.
- Valores técnicos visibles: `None`, `null`, `undefined`.
- Acentos comunes: `próximo`, `análisis`, `competición`, `información`, `conexión`, `membresía`, `país`, `señales`.
- Promesas prohibidas: `garantizado`, `apuesta segura`, `sin riesgo`, `apuesta fija`.

## Aplicado
- Motores V856 devuelven estados españoles seguros:
  - `Sin datos reales`
  - `Esperando proveedor`
  - `Sin directos reales`
  - `Sin picks activos`
  - `Cuotas pendientes`
  - `Resultado pendiente`
  - `Sin pick real publicado`
  - `No hay datos suficientes`
- Check V856 valida mojibake común y promesas prohibidas.
