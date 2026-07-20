# NeMeSiS SHARK PRO - Matriz RACI

R = ejecuta, A = responsable final, C = consultado, I = informado. Una misma persona puede cubrir varios roles hoy, pero los sombreros deben mantenerse separados.

| Proceso | Dirección | IC/Ops | CTO/Arquitectura | Backend/DB | Frontend/UX | Datos deportivos | Telegram | Pagos | Seguridad/Privacidad | QA/Sentinel | Soporte/Comms | Release/DevOps |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Roadmap y claims | A | I | C | I | R | C | C | C | C | C | C | I |
| Release normal | I | C | C | C | C | C | C | C | C | R | I | A/R |
| Incidente P0/P1 | I | A | C | R | C | R | R | R | R | C | R | R |
| Rollback código | I | A | C | C | I | I | I | I | C | R | I | R |
| Restauración DB | I | A | C | A/R | I | C | C | C | R | C | I | C |
| Rotación secreto | I | A | C | C | I | C | C | C | A/R | C | I | R |
| Sports sync/lifecycle | I | C | C | C | I | A/R | I | I | C | R | I | C |
| Publicar pick | I | C | I | C | I | A/R | C | I | C | R | I | I |
| Envío Telegram | I | C | I | C | I | C | A/R | I | C | C | I | I |
| Cobro/reembolso | A | C | I | C | I | I | I | R | C | C | R | I |
| Membresía excepcional | A | C | I | R | I | I | I | C | C | C | R | I |
| Privacidad/DSAR | A | C | I | R | I | I | C | C | R | C | R | I |
| Backup | I | A | C | R | I | I | I | I | C | C | I | R |
| Restore drill | I | A | C | R | I | C | I | C | C | R | I | R |
| Browser/accessibility QA | I | I | I | C | R | I | I | I | C | A/R | I | C |
| Monitor/SLO | I | A | C | R | C | R | R | R | C | R | I | R |
| Comunicación incidente | A | C | I | I | I | C | C | C | C | C | R | I |
| Cambio legal/precios | A | I | I | C | R | I | I | R | C | C | C | I |

## Reglas de segregación

- Quien desarrolla un cambio no debe ser la única persona que autoriza una restauración o reembolso.
- DB restore, rotación de secreto, mensaje masivo y cambio de precio requieren dos roles.
- Sentinel puede abrir/actualizar incidentes, nunca restaurar DB, cobrar o enviar masivos.
- QA puede bloquear un release; no puede falsificar un PASS.
- Soporte puede conceder acceso provisional solo con evidencia y auditoría, no cambiar Stripe.

## Cobertura mínima para beta

Aunque Damian desempeñe varios roles, deben existir al menos:

1. Un operador alternativo con acceso read-only y runbooks.
2. Un segundo aprobador para DB, pagos, secretos y mensajes masivos.
3. Un contacto legal/privacidad.
4. Un responsable de soporte durante la ventana beta.

