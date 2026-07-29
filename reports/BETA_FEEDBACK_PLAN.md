# BETA FEEDBACK PLAN

Fecha Madrid: 2026-07-29

Alcance: recogida de feedback y metricas de primeros usuarios sin activar nuevas funcionalidades.

Produccion modificada: false

Commit/push/deploy: no ejecutados

## Executive Summary

El feedback de beta debe ser pequeno, honesto y util. No se trata de recoger todos los datos posibles, sino de saber si NeMeSiS aporta valor real, donde se pierde el usuario y que bloquea conversion o retencion.

No se activa ningun envio, tracking nuevo, integracion externa ni IA. Este documento define la infraestructura operativa y de medicion que se debe usar cuando la beta se autorice.

## Preguntas De Negocio

1. El usuario entiende que hace NeMeSiS?
2. Encuentra un partido sin ayuda?
3. Entiende SHARK como contexto basado en evidencia?
4. Vuelve al dia siguiente?
5. Ve valor suficiente para PRO o ELITE?
6. Confia en los datos y limitaciones?
7. Puede pedir ayuda?
8. Que friccion impide continuidad?

## Feedback A Recoger

| Categoria | Pregunta | Formato |
| --- | --- | --- |
| Claridad | Que entendiste que hace NeMeSiS? | Texto corto |
| Navegacion | Donde te perdiste? | Texto corto |
| Valor | Que fue lo mas util? | Seleccion + texto |
| SHARK | Te ayudo? Por que? | 1-5 + texto |
| Conversion | Que te haria pagar PRO/ELITE? | Texto corto |
| Confianza | Viste algo exagerado o poco claro? | Si/no + texto |
| Retencion | Volverias manana? | Si/no |
| Soporte | Supiste pedir ayuda? | Si/no |
| Bugs | Que fallo? | Ruta + descripcion |

## Metricas Minimas

| Metrica | Definicion | Estado privacy |
| --- | --- | --- |
| Activacion | Registro + primer acceso | Minimizada |
| Time to value | Tiempo hasta primer partido, SHARK o favorito | Agregada |
| First match | Primer Match Center abierto | ID de entidad, no PII |
| First team | Primer Team Center abierto | ID de entidad |
| First competition | Primer Competition Center abierto | ID de entidad |
| First player | Primer Player Center abierto | ID de entidad |
| First SHARK | Primer uso SHARK | Evento interno |
| Favorite created | Favorito creado por usuario | Control usuario |
| Return D1 | Vuelve al dia siguiente | Agregado |
| Return D7 | Vuelve dentro de 7 dias | Agregado |
| Plan viewed | Visita membresias | Evento interno |
| Upgrade intent | Click o respuesta declarada | No conversion inventada |
| Support contact | Solicitud de ayuda | Ticket minimo |

## Datos Que No Se Deben Recoger

- claves;
- passwords;
- tokens;
- tarjetas;
- mensajes privados externos;
- IP completa salvo necesidad legal;
- fingerprint invasivo;
- datos sensibles;
- inferencias no respaldadas;
- informacion de otras plataformas;
- conversiones o ingresos inventados.

## Privacidad

La recogida debe seguir User Intelligence:

- transparencia;
- consentimiento;
- control del usuario;
- exportacion;
- reinicio;
- borrado;
- desactivacion;
- sin terceros.

Si alguna metrica no puede recogerse respetando esos principios, queda como `NOT_CERTIFIED`, no se inventa.

## Proceso De Feedback

### Durante sesion

- Observar sin interrumpir.
- Registrar tiempo hasta primer valor.
- Anotar confusion literal.
- No corregir al usuario salvo bloqueo.

### Despues de sesion

- Enviar encuesta corta.
- Registrar severidad de problemas.
- Separar bug, UX, soporte y conversion.
- Crear tarea solo si hay evidencia.

### Semanalmente

- Revisar patrones.
- Agrupar problemas repetidos.
- Priorizar P1/P2.
- Decidir si se amplia beta o se pausa.

## Clasificacion De Feedback

| Tipo | Ejemplo | Accion |
| --- | --- | --- |
| Bug | Error 500, ruta rota | P1/P2 segun impacto |
| Confusion | No entiende SHARK | Copy/onboarding |
| Friccion | Muchos clicks | UX backlog |
| Valor | "Volveria por favoritos" | Reforzar |
| Conversion | "Pagaria si..." | Hipotesis comercial |
| Soporte | No sabe cancelar | Runbook/copy |
| Riesgo | Cree que gana seguro | P1 legal/copy |

## Decision De Aprendizaje

No basta una opinion aislada. Una decision de producto requiere:

- al menos 3 usuarios con la misma senal, o
- 1 fallo P1/P0 demostrado, o
- evidencia cuantitativa clara, o
- riesgo legal/privacidad/pago.

## Reporte Semanal De Beta

Debe incluir:

- usuarios invitados;
- usuarios activos;
- primer partido;
- primer SHARK;
- favoritos;
- retorno D1/D7;
- feedback positivo;
- feedback negativo;
- bugs;
- dudas de pago;
- dudas de Telegram;
- problemas de soporte;
- decisiones tomadas;
- decisiones pendientes.

## Criterio Para Ampliar Beta

Ampliar solo si:

- no hay P1 abierto;
- soporte responde;
- usuarios entienden valor;
- no hay confusion grave sobre SHARK;
- pagos/Telegram no generan riesgo;
- retencion inicial existe o hay aprendizaje claro.

## Siguiente Unica Accion

Hacer una beta interna de 3 usuarios y completar una ficha por usuario antes de abrir la beta cerrada externa de 10-25 personas.
