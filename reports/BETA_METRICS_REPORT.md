# Beta Metrics Report

## Principle

Las m?tricas beta son transparentes, agregadas y desactivables por env?o. No sustituyen satisfacci?n real, conversi?n ni ?xito comercial si no existe muestra suficiente.

## Metrics

| m?trica | valor | fuente | definici?n | limitaci?n | desactivable |
| --- | --- | --- | --- | --- | --- |
| Feedback recibido | 4 | beta_feedback | Total de envios explicitos realizados desde el Beta Center. | No incluye conversaciones externas ni mensajes no registrados. | True |
| Bugs reportados | 1 | beta_feedback | Envios clasificados como bug con estructura reproducible. | Un bug reportado no equivale a bug confirmado hasta revision humana. | True |
| Solicitudes | 1 | beta_feedback | Envios clasificados como solicitud de mejora. | No implica aprobaci?n de roadmap. | True |
| Satisfacci?n media | 4.0 | beta_feedback | Media de puntuaciones 1-5 enviadas voluntariamente. | No se interpreta con muestras peque?as. | True |
| Metricas aceptadas | 3 | beta_feedback | Envios donde el usuario permite usar el feedback para m?tricas agregadas. | El usuario puede desactivar esta medici?n en cada envio. | True |
| Metricas desactivadas | 1 | beta_feedback | Envios donde el usuario no permite uso agregado para m?tricas. | El feedback se conserva para soporte si se envio, pero no se usa en m?tricas agregadas. | True |


## Source

Todas las m?tricas proceden de `beta_feedback`, creada localmente por env?os expl?citos del usuario.

## Not Stored

- Correos.
- Tel?fonos.
- Tarjetas.
- Contrase?as.
- Tokens.
- Claves API.
- Datos deportivos inventados.

## External Calls

0 llamadas externas, 0 Telegram, 0 Stripe, 0 producci?n.
