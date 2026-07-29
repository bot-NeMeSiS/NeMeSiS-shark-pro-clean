# SUPPORT RUNBOOK

Fecha Madrid: 2026-07-29

Alcance: soporte beta cerrada de NeMeSiS SHARK PRO.

Produccion modificada: false

Commit/push/deploy: no ejecutados

## Objetivo

Dar respuesta rapida, honesta y trazable a los primeros usuarios sin improvisar y sin tocar produccion de forma peligrosa.

## Principios

- Responder con claridad.
- No prometer resultados deportivos.
- No pedir datos sensibles por chat si no hace falta.
- No mostrar secretos.
- No modificar pagos, DB, Telegram o membresias sin autorizacion.
- Separar duda, bug, incidente y solicitud comercial.

## Canales

| Canal | Uso | Estado |
| --- | --- | --- |
| Formulario soporte `/support` | Contacto general y errores | Disponible localmente |
| Admin Support Center `/admin/support-center` | Revision interna | Disponible localmente |
| Contacto manual del operador | Beta cerrada | Debe definirse antes de invitar usuarios |
| Telegram | Solo si autorizado | No usar como soporte masivo inicialmente |

## Clasificacion

| Tipo | Severidad | Ejemplos | Tiempo objetivo beta |
| --- | --- | --- | --- |
| Acceso | P1/P2 | No puede entrar, password, registro | <8h |
| Pago/membresia | P0/P1 | Cobro, plan no activo, cancelacion | <4h |
| Datos deportivos | P1/P2 | Falso live, stale, partido incorrecto | <24h |
| Telegram | P1/P2 | Duplicado, no recibido, destino incorrecto | <8h |
| UX | P2/P3 | No entiende, texto confuso, movil roto | <48h |
| Privacidad | P0/P1 | Borrado, exportacion, dato visible | <4h |
| Seguridad | P0 | Secreto, acceso indebido | inmediato |

## Flujo General

1. Registrar solicitud.
2. Clasificar tipo y severidad.
3. Confirmar si afecta a un usuario o a varios.
4. Pedir solo datos necesarios.
5. Reproducir localmente si procede.
6. Consultar Operations Center/Sentinel si es tecnico.
7. Responder con estado honesto.
8. Cerrar solo con evidencia.

## Respuestas Base

### Acceso

"Gracias por avisar. Vamos a revisar el acceso sin pedirte contrasenas. Dime que paso: registro, login o recuperacion. Si aparece un mensaje, copia solo el texto visible, sin datos sensibles."

### Pago

"Durante beta tratamos los pagos con control especial. No vamos a hacer ningun cargo ni cambio sin confirmarlo contigo. Revisaremos el estado del plan y te diremos que evidencia tenemos."

### Telegram

"Telegram puede estar limitado durante la beta. Revisaremos si el destino esta autorizado, si el mensaje fue bloqueado por dedupe o si el envio esta desactivado por seguridad."

### Datos deportivos

"NeMeSiS nunca rellena datos sin evidencia. Si algo aparece como no disponible o antiguo, lo revisaremos contra la frescura y la fuente disponible."

### SHARK

"SHARK no garantiza resultados. Su funcion es ayudarte a entender contexto, evidencia y limitaciones. Si una explicacion no esta clara, la revisamos."

### Privacidad

"Puedes pedir exportar, reiniciar o borrar tus preferencias de personalizacion. No vendemos datos ni enviamos preferencias a terceros."

## Procedimientos

### Recuperacion De Cuenta

- Confirmar identidad por canal autorizado.
- No pedir password.
- No enviar credenciales en claro.
- Usar flujo existente si esta disponible.
- Si no, escalar a Owner.

### Cancelacion

- Confirmar plan y estado.
- No cancelar automaticamente sin confirmacion.
- Documentar fecha, usuario y motivo.
- Si Stripe real no esta certificado, resolver manualmente con Owner.

### Error De Membresia

- Confirmar plan visible para usuario.
- Revisar admin memberships.
- Confirmar si pago existe o es beta manual.
- No modificar DB directamente.
- Escalar si hay cobro sin acceso.

### Dato Deportivo Incorrecto

- Registrar partido, competicion, hora Madrid y captura si existe.
- Confirmar frescura y fuente.
- Si afecta picks o Telegram, pausar comunicaciones relacionadas.
- No inventar correccion.

### Incidente P0/P1

- Avisar Owner/CTO.
- Detener acciones automaticas relacionadas.
- Guardar evidencia.
- No desplegar ni restaurar sin decision.
- Seguir `INCIDENT_RESPONSE_PLAN.md`.

## Campos Minimos Del Ticket

- fecha Madrid;
- usuario beta o identificador interno;
- tipo;
- severidad;
- pantalla/ruta;
- descripcion;
- pasos para reproducir;
- impacto;
- evidencia;
- respuesta enviada;
- owner;
- estado;
- cierre.

## Errores Frecuentes Esperados En Beta

- No entender donde empezar.
- Confundir SHARK con prediccion.
- No distinguir PRO y ELITE.
- Esperar Telegram inmediato.
- Encontrar "No disponible" y pensar que es fallo.
- Pedir datos que aun no existen.
- Dudas de cancelacion y pagos.

## Criterio De Cierre

Un ticket se cierra solo si:

- el usuario recibio respuesta;
- el estado esta documentado;
- no queda accion pendiente;
- si hubo bug, existe evidencia de validacion;
- si hubo riesgo P1/P0, se creo prevencion.

## Siguiente Unica Accion

Nombrar un responsable de soporte beta y fijar un canal unico antes de invitar al primer usuario.
