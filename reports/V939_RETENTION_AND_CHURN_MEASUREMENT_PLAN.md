# V939 Plan de retencion y churn

## Retencion

Definir cohortes por fecha de alta y medir actividad real a D1, D7 y D30. Se requiere identificador interno, consentimiento aplicable y ventana fija.

## Churn

Separar cancelacion solicitada, expiracion, fallo de pago y downgrade. El denominador debe ser membresias renovables al inicio de la ventana.

## Guardrails

- Muestra minima 10 por cohorte para una lectura descriptiva inicial.
- No mostrar porcentaje con denominador 0.
- No atribuir churn a una pantalla sin experimento valido.
- No almacenar PII adicional.

Estado actual: `INSUFFICIENT_DATA`.
