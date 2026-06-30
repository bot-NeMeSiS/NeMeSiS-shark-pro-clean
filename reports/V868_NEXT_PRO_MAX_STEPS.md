# V868 Pro Max - Próximos pasos

## Orden recomendado
1. Desplegar V868 Pro Max en Render y comparar runtime real contra local.
2. Ejecutar Browser QA real autenticado en móvil y PC con capturas nuevas de V868 Pro Max.
3. Revisar rutas de pago/membresía con Stripe configurado en entorno seguro.
4. Validar Telegram real solo con autorización explícita y canal de prueba.
5. Auditar API-SPORTS en producción con cuotas de consumo y caché.
6. Revisar picks/live con datos reales del día.
7. Convertir hallazgos Sentinel en tareas pequeñas y medibles.

## No tocar sin validación
- Secretos.
- DB_PATH.
- Usuarios o pagos reales.
- Envíos Telegram reales.
- Llamadas externas caras.
