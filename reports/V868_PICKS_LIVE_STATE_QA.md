# V868 Picks y Live State QA

Estados preservados y reforzados:

- Cuotas pendientes.
- Selección pendiente.
- Pick en revisión.
- Sin pick real publicado.
- Proveedor sin datos ahora mismo.
- Sin directos reales.
- Esperando proveedor.

Validación funcional:

- No se muestra cuota `None`, `null`, `undefined` como valor comercial.
- No se inventa marcador, minuto, selección ni cuota.
- Live mantiene cache-first y guard anti-gasto de V847/V850.
- Picks incompletos se muestran como revisión o pendiente, no como oportunidad final.
