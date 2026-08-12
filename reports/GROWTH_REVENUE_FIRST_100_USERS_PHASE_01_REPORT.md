# First 100 Users - Growth & Revenue OS Phase 01

Fecha de certificacion local: 12 de agosto de 2026 (Europe/Madrid).

## Executive Summary

- **Decision: ACQUISITION_READY LOCAL.** NeMeSiS puede iniciar una captacion manual y controlada de los primeros 10 usuarios. La instrumentacion, la landing, la atribucion, el soporte, el contenido y el panel fundador estan preparados.
- **La evidencia de crecimiento sigue siendo insuficiente.** No hay una cohorte real de adquisicion, canal ganador, CAC, MRR, churn ni retencion certificada. La preparacion de la maquina no equivale a exito comercial.
- **El primer valor ya es medible.** Se registra cuando una cuenta autenticada abre un Match Center canonico con partido resoluble. La activacion exige, ademas, guardar un favorito o abrir un segundo partido distinto.
- **No se ha publicado, enviado ni gastado nada.** FIRST_10_USERS y todo el contenido quedan en revision humana; paid ads permanece con gasto cero.

## La maquina ya puede buscar los primeros 10 usuarios

La condicion de salida de FOUNDATION_READY se cumple localmente porque existen: contrato de eventos versionado, atribucion UTM minimizada, FIRST_VALUE y ACTIVATED definidos, landing CRO, campaña manual, 29 piezas en revision, SEO tecnico local, diez experimentos y panel First 10/25/50/100.

**Implicacion:** el fundador puede invitar manualmente a una primera cohorte y aprender sin activar publicidad, envios masivos ni pagos reales.

## Definiciones que gobiernan el funnel

### FIRST_VALUE

Un usuario autenticado alcanza FIRST_VALUE cuando abre un Match Center canonico asociado a un partido real resoluble. Esta accion entrega el valor central, usa una entidad canonica y es medible sin PII. Buscar un partido es un paso previo; guardar un favorito es una señal posterior.

### ACTIVATED_USER

Un usuario queda ACTIVATED cuando ya alcanzo FIRST_VALUE y despues guarda un favorito o abre un segundo Match Center canonico distinto. La activacion no se concede por registro, login, scroll ni visita a precios.

## Funnel completo y evidencia

| Etapa | Definicion inicial | Evidencia disponible | Estado sin evidencia |
| --- | --- | --- | --- |
| DISCOVERY | La cuenta registrada conserva un canal minimizado | Fuente/canal vinculados al registro, no visitantes anonimos | INSUFFICIENT_REAL_DATA |
| LANDING | Visita publica temporal en la sesion | Sesion local, no persistida sin consentimiento | INSUFFICIENT_REAL_DATA |
| REGISTRATION | Cuenta creada correctamente | Usuario agregado y evento deduplicado | INSUFFICIENT_REAL_DATA |
| FREE | Cuenta en plan FREE | Plan agregado | INSUFFICIENT_REAL_DATA |
| FIRST_VALUE | Primer Match Center canonico abierto | Evento autenticado con match id seguro | INSUFFICIENT_REAL_DATA |
| ACTIVATED | FIRST_VALUE + favorito o segundo partido | Evento autenticado deduplicado | INSUFFICIENT_REAL_DATA |
| RETURNING | Regreso autenticado en otro dia | Actividad diaria deduplicada | INSUFFICIENT_REAL_DATA |
| PREMIUM_INTENT | Vista autenticada de membresias | Evento propio del producto | INSUFFICIENT_REAL_DATA |
| PRO | Plan PRO agregado | Estado de membresia; no equivale a MRR | INSUFFICIENT_REAL_DATA |
| ELITE | Plan ELITE agregado | Estado de membresia; no equivale a MRR | INSUFFICIENT_REAL_DATA |
| RETAINED | Uso sostenido en ventana certificada | Requiere cohorte y tiempo | INSUFFICIENT_REAL_DATA |
| REFERRAL | Invitado registra y alcanza valor | MVP diseñado, no activo | INSUFFICIENT_REAL_DATA |

Tasas oficiales: visitor_to_registration, registration_to_first_value, first_value_to_activation, activation_to_returning, free_to_premium_intent y premium_intent_to_paid. Sin denominador real se muestra 0 / INSUFFICIENT_REAL_DATA. visitor_to_registration no se estima porque NeMeSiS no persiste visitantes anonimos sin consentimiento.

## Lo que podemos medir ya

- registros autenticados;
- FIRST_VALUE por cuenta;
- activacion por favorito o segundo partido;
- retorno en un dia posterior;
- intencion premium;
- plan FREE, PRO o ELITE agregado;
- canal y campaign_id minimizados al registrar;
- progreso separado REGISTERED, ACTIVATED, RETURNING y PAID;
- incidencias y feedback agregados disponibles en soporte.

## Lo que todavia no podemos afirmar

- visitantes unicos persistentes o conversion visitante-registro;
- canal ganador, CAC o impacto real de contenido;
- retencion por cohorte madura;
- MRR, churn o LTV certificados;
- disposicion real a pagar;
- rendimiento SEO en produccion;
- conversion de referral o eficacia de anuncios.

Cualquier dashboard mantiene estos huecos como INSUFFICIENT_REAL_DATA, no como cero comercial.

## Primera campaña organica

FIRST_10_USERS esta en READY_FOR_REVIEW.

- Objetivo: 10 registros reales y observar cuantos llegan a FIRST_VALUE y ACTIVATED.
- Audiencia: adultos apropiados del circulo propio, invitaciones beta y comunidades que permitan promocion.
- Mensaje: beta cerrada para seguir partidos con contexto, evidencia y limites visibles.
- Landing: /landing?utm_source=referral&utm_medium=manual&utm_campaign=FIRST_10_USERS.
- CTA: EMPEZAR GRATIS.
- Seguimiento: registro, FIRST_VALUE, ACTIVATED, RETURNING, feedback y soporte.
- Stop conditions: queja de privacidad, ruta rota, promesa ambigua, soporte saturado o dato ficticio.
- Envio automatico: no.

El contenido completo esta en reports/FIRST_10_USERS_CAMPAIGN_PACK.md.

## Plan social sin publicacion

| Canal | Bio propuesta | Frecuencia | KPI primario | CTA | Restriccion |
| --- | --- | --- | --- | --- | --- |
| Instagram | Partidos con contexto, evidencia y limites | 3/semana | ACTIVATED atribuidos | Empezar gratis | Sin imagenes protegidas |
| TikTok | Entiende el partido antes del ruido | 3/semana | FIRST_VALUE atribuidos | Ver un partido | +18 cuando aplique |
| YouTube | Guias breves de Match Center y SHARK | 1/semana | FIRST_VALUE atribuidos | Probar NeMeSiS | Solo recursos propios |
| X | Contexto deportivo verificable, sin promesas | 4/semana | Registros cualificados | Abrir beta | Sin actualidad sin fuente |
| Facebook | Deporte claro para seguir equipos | 2/semana | ACTIVATED atribuidos | Empezar gratis | No targeting vulnerable |
| Telegram | Briefings opt-in con evidencia | 2/semana | Retorno opt-in | Revisar en NeMeSiS | Sin envio masivo |

Nombre en todos los canales: NeMeSiS SHARK PRO. Link: landing FIRST_10_USERS. No se han creado cuentas ni publicaciones.

## Plan SEO

**PASS local:** robots, sitemap, canonical, titles, descriptions, Open Graph, datos estructurados en landing e internal linking existen.

1. P0: certificar Core Web Vitals con observacion de produccion.
2. P1: publicar tres contenidos evergreen aprobados y enlazarlos desde ayuda.
3. P1: validar indexacion real tras despliegue.
4. P2: ampliar datos estructurados solo donde exista contenido real.

No se crean paginas programaticas masivas.

## Plan CRM opt-in

| Journey | Trigger | Valor | Estado |
| --- | --- | --- | --- |
| WELCOME | REGISTRATION | Abrir calendario y primer partido | READY_FOR_REVIEW |
| FIRST_VALUE_HELP | Registro sin FIRST_VALUE | Reducir friccion inicial | READY_FOR_REVIEW |
| ACTIVATION_HELP | FIRST_VALUE sin activacion | Explicar favorito o segundo partido | READY_FOR_REVIEW |
| SHARK_DISCOVERY | FIRST_VALUE | Explicar evidencia y limites | READY_FOR_REVIEW |
| FAVORITES | Activacion por favorito | Facilitar retorno | READY_FOR_REVIEW |
| PREMIUM_EDUCATION | PREMIUM_INTENT | Comparar planes sin presion | READY_FOR_REVIEW |
| INACTIVE | Sin retorno en ventana certificada | Ofrecer ayuda | READY_FOR_REVIEW |
| RETURN | RETURNING | Recuperar contexto guardado | READY_FOR_REVIEW |
| CANCELLATION | Solicitud de baja | Baja clara y soporte | READY_FOR_REVIEW |
| WINBACK | Baja + consentimiento | Informar sin urgencia engañosa | READY_FOR_REVIEW |

Envio automatico: no. Consentimiento y baja: obligatorios donde corresponda.

## Referral MVP

Flujo diseñado: usuario comparte enlace seguro -> amigo registra -> amigo alcanza FIRST_VALUE -> amigo puede quedar ACTIVATED.

Eventos: referral_sent, referral_registration y referral_activated. No hay recompensa monetaria, activacion automatica ni enlace publico. Requiere revision legal, antiabuso y aprobacion del fundador.

## FREE -> PRO -> ELITE

- **FREE vende confianza:** calendario, directo, resultados y SHARK base permiten probar valor.
- **PRO vende continuidad:** mas contexto, seguimiento y Telegram premium cuando cada capacidad este certificada.
- **ELITE vende intensidad:** alertas live, prioridad Telegram y SHARK contextual, tambien sujetas a certificacion.
- **Momentos naturales de upgrade:** FIRST_VALUE, favorito recurrente, preview premium, briefing diario o Telegram opt-in.
- **Dark patterns:** prohibidos.

Precios de referencia: FREE 0 EUR, PRO 9,99 EUR/mes, ELITE 24,99 EUR/mes. Los identificadores Stripe PRO/ELITE no estan certificados. Decision: NO_CHANGE_RECOMMENDED; no existe evidencia de conversion, disposicion a pagar o churn que justifique cambiar precios.

## Top 10 experimentos

| ID | Hipotesis | Metrica | Estado |
| --- | --- | --- | --- |
| EXP-001 | CTA Empezar gratis reduce ambiguedad | registration_to_first_value | READY |
| EXP-002 | Primer partido guiado acelera valor | registration_to_first_value | READY |
| EXP-003 | Feedback tras FIRST_VALUE mejora calidad | feedback_completion | READY |
| EXP-004 | Casos de uso aclaran planes | free_to_premium_intent | READY |
| EXP-005 | SHARK explicable aumenta confianza | visitor_to_registration | READY |
| EXP-006 | Favorito como segundo paso mejora activacion | first_value_to_activation | READY |
| EXP-007 | Briefing de retorno ayuda a volver | activation_to_returning | READY |
| EXP-008 | Metodologia atrae usuarios cualificados | registration_to_first_value | READY |
| EXP-009 | Invitacion personal supera mensaje generico | registration_to_first_value | READY |
| EXP-010 | Ayuda visible reduce abandono | registration_completion | READY |

Baseline: INSUFFICIENT_REAL_DATA. Ninguno se ejecuta automaticamente.

## Paid Ads Lab sin gasto

META_TEST_01 y GOOGLE_TEST_01 estan en DRAFT_NO_SPEND. Exigen audiencia legal, landing aprobada, creatividad revisada, presupuesto propuesto, KPI de ACTIVATED, stop condition y compliance. Gasto ejecutado: 0. TikTok Ads queda fuera de la fase inicial.

## Customer Success para 100 usuarios

La base reutiliza onboarding, FAQ, Help Center, soporte, bug report, feedback, recuperacion de cuenta, ayuda de cancelacion y satisfaccion. Founder Center resume incidencias agregadas. La capacidad de pago sigue condicionada a Stripe y el abandono anonimo previo al registro no puede medirse sin consentimiento.

## Que hara NeMeSiS automaticamente

- conservar atribucion minimizada durante la sesion;
- registrar eventos autenticados deduplicados;
- calcular FIRST_VALUE, ACTIVATED, RETURNING y PREMIUM_INTENT;
- separar REGISTERED, ACTIVATED, RETURNING y PAID;
- preparar Founder Growth Center y Product + Growth + Revenue Brief;
- mostrar huecos de evidencia;
- preparar contenido y experimentos para revision.

## Que debe hacer manualmente el fundador

- aprobar mensaje y piezas FIRST_10_USERS;
- elegir destinatarios adultos y canales permitidos;
- enviar invitaciones controladas;
- revisar feedback y soporte;
- aprobar publicaciones, journeys, referral y experimentos;
- certificar Stripe antes de cobrar;
- aprobar presupuesto antes de paid ads;
- decidir que aprendizajes pasan al roadmap.

## Siguiente paso recomendado

Aprobar manualmente FIRST_10_USERS y enviar una primera tanda controlada de invitaciones. No ampliar a 25 hasta comprobar FIRST_VALUE, activacion y capacidad de soporte.

## Preguntas abiertas

- Que porcentaje de registros alcanza FIRST_VALUE?
- La segunda accion elegida representa activacion real?
- Que canal produce ACTIVATED, no solo registros?
- Que objecion aparece antes de PREMIUM_INTENT?
- La referencia de precios resulta clara antes de activar Stripe?

## Caveats and Assumptions

Esta es una certificacion local. No certifica produccion, Render, indexacion real, entrega social, Telegram, Stripe, ingresos ni usuarios reales. No se han realizado llamadas externas, publicaciones, comunicaciones masivas, gasto, push ni deploy.