# BETA ACCEPTANCE CHECKLIST

Fecha Madrid: 2026-07-29

Alcance: beta cerrada de primeros usuarios reales.

Produccion modificada: false

Commit/push/deploy: no ejecutados

## Decision Ejecutiva

NeMeSiS puede preparar una beta cerrada, pero no debe abrirse a usuarios reales hasta pasar este checklist. El objetivo de la beta no es escalar ventas: es validar que un usuario real entiende el producto, encuentra valor, puede pedir ayuda y no queda expuesto a pagos, Telegram o datos deportivos no certificados.

Estado actual recomendado: PRE_BETA_READY_LOCAL, BETA_LAUNCH_PENDING_GATES.

## Principio De La Beta

La beta cerrada debe responder una sola pregunta:

¿Puede un usuario utilizar NeMeSiS durante varias semanas, entender el valor, volver por iniciativa propia y darnos evidencia real sin riesgo operativo, legal o reputacional?

## Gates Obligatorios

| Gate | Criterio | Estado inicial | Evidencia requerida |
| --- | --- | --- | --- |
| Produccion | Runtime, health y SHA certificados antes de invitar usuarios | PENDING | `/api/runtime-version`, `/api/health`, Home 200 |
| Registro | Crear cuenta sin friccion y sin errores visibles | PENDING | Browser QA + prueba humana |
| Login | Login estable, logout claro y recuperacion prevista | PENDING | Browser QA + prueba humana |
| Primer acceso | El usuario entiende donde empezar | PENDING | Test con 3-5 usuarios internos |
| Primer partido | Usuario encuentra un partido en menos de 3 minutos beta | PENDING | Observacion o feedback |
| Primer centro deportivo | Match/Team/Competition/Player Center no generan confusion | PENDING | Observacion o feedback |
| SHARK | Usuario entiende que SHARK explica evidencia, no promete resultados | PENDING | Pregunta directa de comprension |
| Membresias | FREE/PRO/ELITE se entienden sin presion agresiva | PENDING | Revision copy + feedback |
| Pagos | Stripe test completo si hay cobro o checkout visible | BLOCKER | Checkout -> webhook -> membresia -> cancelacion |
| Telegram | Solo canal/control autorizado; dedupe y limites verificados | BLOCKER | Dry-run + envio controlado si se autoriza |
| Soporte | Canal, tiempos y respuestas base definidos | PENDING | `SUPPORT_RUNBOOK.md` operativo |
| Privacidad | User Intelligence transparente y desactivable | PENDING | Revision de centro de privacidad |
| Datos deportivos | Frescura, stale y false-live claros | PENDING | Data QA read-only |
| Backups | Restore aislado ejecutado antes de beta ampliada | PENDING | Drill documentado |
| Incidentes | Runbook P0/P1 listo | PENDING | Owner y canal definidos |

## Onboarding

### Registro

El registro debe:

- pedir solo datos necesarios;
- explicar que la beta es cerrada;
- no prometer beneficios deportivos o economicos;
- dejar claro que NeMeSiS no es casa de apuestas;
- dirigir al primer uso sin obligar a pagar.

Aceptacion:

- el usuario puede registrarse;
- no ve errores tecnicos;
- entiende que empieza en FREE;
- sabe donde continuar.

### Login

El login debe:

- aceptar credenciales validas;
- fallar de forma humana si hay error;
- no revelar detalles tecnicos;
- ofrecer ruta de recuperacion o soporte.

Aceptacion:

- login/logout funcionan;
- recuperacion esta explicada aunque sea manual;
- soporte aparece si no puede entrar.

### Primer Acceso

El primer acceso debe llevar a:

1. descubrir partidos;
2. abrir un partido;
3. entender el contexto;
4. ver SHARK como ayuda contextual;
5. crear un favorito o volver al calendario.

No debe llevar primero a:

- pago;
- panel admin;
- estados tecnicos;
- configuraciones largas;
- Telegram sin contexto.

## Conversion FREE -> PRO -> ELITE

| Plan | Valor que debe entenderse | Riesgo beta | Criterio |
| --- | --- | --- | --- |
| FREE | Descubrir partidos y contexto basico | Que parezca demasiado limitado | Usuario encuentra valor sin pagar |
| PRO | Ahorro de tiempo, picks responsables, Telegram util | Que parezca promesa de acierto | Copy responsable y ejemplos reales |
| ELITE | Mayor profundidad, seguimiento y bankroll responsable | Que parezca presion comercial | Transparencia y no prometer ROI |

Aceptacion:

- no hay lenguaje de garantia;
- el usuario sabe que paga por contexto, seguimiento y ahorro de tiempo;
- los bloqueos premium no impiden entender el producto;
- el upgrade no oculta riesgos deportivos.

## Soporte

Antes de beta:

- canal de contacto definido;
- respuesta base para login, pago, Telegram, datos, privacidad y cancelacion;
- responsable humano asignado;
- tiempo maximo de respuesta beta definido;
- proceso de escalado P0/P1.

## Feedback

La beta debe recoger:

- errores;
- sugerencias;
- confusion;
- valor percibido;
- motivos de retorno;
- motivos de abandono;
- interes en PRO/ELITE.

No debe recoger:

- datos sensibles innecesarios;
- IP completa salvo necesidad legal;
- preferencias inferidas sin evidencia;
- informacion fuera de NeMeSiS;
- datos enviados a terceros.

## Metricas Minimas

| Metrica | Definicion beta | Privacidad |
| --- | --- | --- |
| Primer uso | Usuario abre la app tras registro | Evento minimo interno |
| Tiempo hasta valor | Tiempo hasta abrir partido, SHARK o favorito | Sin PII innecesaria |
| Uso diario | Sesiones por dia | Agregado |
| Uso semanal | Usuarios que vuelven en 7 dias | Agregado |
| Retencion | Retorno D1/D7 | Agregado |
| Primer partido | Primer Match Center abierto | ID interno de entidad |
| Primer favorito | Favorito creado | Controlado por usuario |
| Primer SHARK | SHARK abierto y comprendido | Feedback explicito |
| Conversion intent | Plan visitado o interes declarado | No inventar conversion |

## Criterios GO Para Beta Cerrada

- Produccion certificada read-only en el SHA que se va a usar.
- Registro/login/primer acceso revisados.
- Browser QA y Sentinel PASS.
- Stripe y Telegram no se usan de forma real salvo certificacion y autorizacion.
- Soporte listo.
- Limitaciones visibles para el equipo.
- 10-25 usuarios maximo en primera tanda.
- Feedback manual preparado.
- Rollback y backup conocidos.

## Criterios NO-GO

- P1 abierto.
- Pagos no certificados y visibles como reales.
- Telegram real no controlado.
- Restore no documentado para beta ampliada.
- Datos stale sin explicacion.
- SHARK presentado como prediccion o garantia.
- Soporte sin responsable.

## Siguiente Unica Accion

Ejecutar una prueba interna con 3 usuarios de confianza siguiendo `FIRST_USERS_GUIDE.md`, sin pagos reales y sin Telegram real, para validar si entienden el producto en menos de 20 minutos.
