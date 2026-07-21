# V939 Reglas de muestra y confianza SHARK

- Muestra global minima: 30 picks evaluables.
- Muestra minima por segmento: 20 picks evaluables.
- Winrate: solo ganado/perdido; void no entra en denominador.
- ROI: solo cuando stake y beneficio real estan persistidos en al menos la muestra minima.
- Calibracion: solo con confianza registrada y resultado cerrado.
- Segmentos: mercado, competicion, rango de cuota, riesgo, stake, hora y proveedor.
- Ausencia de muestra: metrica `null`, estado `INSUFFICIENT_DATA`.
- Asociacion historica: nunca se presenta como causalidad.

Estas reglas son un primer guardrail conservador. Modificarlas requiere revision y una justificacion documentada.
