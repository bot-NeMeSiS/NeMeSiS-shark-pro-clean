# Growth & Revenue OS - First Real Users Launch

Fecha de certificación local: 2026-08-12 (Europe/Madrid)

## Decisión

**LIVE_ACQUISITION_READY_LOCAL**.

La infraestructura local puede medir `REGISTRATION`, `FIRST_VALUE`, `ACTIVATED`, `RETURNING` y `PREMIUM_INTENT`, separando de forma obligatoria `REAL_USER`, `SIMULATED_QA` y eventos antiguos `UNKNOWN`. No existe lanzamiento real, publicación, gasto, envío masivo, cobro ni despliegue en este sprint.

Producción permanece **BLOCKED_UNTIL_PUSH_AND_DEPLOY**. El enlace FIRST100 no debe compartirse hasta que el código certificado llegue a `origin/main`, Render complete un despliegue controlado y el recorrido se verifique allí en modo seguro.

## Git y producción

- Rama: `main`.
- El bloque Growth/First100 fue cerrado primero en un commit local selectivo.
- El código de endurecimiento LIVE_ACQUISITION se incorpora al mismo cierre local únicamente después de QA completa.
- Push: no ejecutado.
- Deploy: no ejecutado.
- Producción modificada: no.

| Gate | Estado | Evidencia | Acción pendiente |
| --- | --- | --- | --- |
| Git | PASS LOCAL | Cambios revisados y QA enfocada PASS | Confirmar commit final local |
| Render | BLOCKED | El código local no está desplegado | Push y deploy requieren autorización separada |
| Funnel | PASS LOCAL | Contrato de 12 etapas y prueba controlada completa | Repetir smoke en producción |
| Attribution | PASS LOCAL | 9 rutas minimizadas, sin PII ni fingerprinting | Confirmar URL pública en Render |
| Landing | PASS LOCAL | CTA, canonical, description y evento de sesión | Observar respuesta real tras deploy |
| Registration/Login | PASS LOCAL | Recorrido temporal con CSRF | Smoke controlado en producción |
| FIRST_VALUE | PASS LOCAL | Match Center canónico QA production-like | Confirmar primer evento REAL_USER |
| ACTIVATED | PASS LOCAL | Segundo partido distinto activa sin falso positivo | Confirmar primer evento REAL_USER |
| Founder Center | PASS LOCAL | Enlaces copiables, hitos separados, revisión editorial y Browser QA en tres tamaños | Observar métricas reales tras despliegue |
| Privacy | PASS LOCAL | Sin URL completa, IP, user agent, fingerprint o PII en evento | Revisión legal humana permanece necesaria |

## Atribución FIRST100

Canales certificados localmente: `DIRECT`, `INSTAGRAM`, `TIKTOK`, `YOUTUBE`, `X`, `FACEBOOK`, `TELEGRAM`, `REFERRAL` y `ORGANIC_SEARCH`.

- Campaña: `FIRST100_ORGANIC`.
- Directo se conserva sin UTM para no falsear la procedencia.
- Referral usa un código funcional común, no un identificador personal.
- El Founder Center genera enlaces absolutos cuando `PUBLIC_BASE_URL`, `APP_PUBLIC_URL` o `RENDER_EXTERNAL_URL` está disponible; en local muestra rutas relativas honestas.

Primer enlace medible preparado para contacto directo, todavía no autorizado para envío:

`https://bot-apuestas-crgf.onrender.com/landing?utm_source=referral&utm_medium=manual&utm_campaign=FIRST100_ORGANIC&ref=first100-founder`

## Kit de primeros 10 usuarios

### A. Contacto directo

- Mensaje: invitación personal a probar un partido real y dar feedback.
- CTA: Abrir NeMeSiS.
- Seguimiento: uno, 24-48 horas después, solo si la persona aceptó probar.
- Métrica: `REGISTRATION -> FIRST_VALUE -> ACTIVATED`.
- Estado: `READY_NOT_SENT`.

### B. Redes propias

- Mensaje: menos ruido, más contexto y ninguna afirmación sin evidencia.
- CTA: Empezar gratis.
- Métrica: canal atribuido, FIRST_VALUE y ACTIVATED; no solo impresiones.
- Estado: `READY_NOT_PUBLISHED`.

### C. Comunidades permitidas

- Requiere leer reglas y autorización de moderación.
- Una publicación, sin repetición ni urgencia falsa.
- Retirada inmediata si lo solicita la comunidad.
- Estado: `REQUIRES_COMMUNITY_PERMISSION`.

## Calendario orgánico de siete días

| Día | Canal | Pieza | Objetivo | Estado |
| --- | --- | --- | --- | --- |
| 1 | Instagram | POST-10 | Registro beta | READY_FOR_REVIEW |
| 2 | TikTok | REEL-01 | FIRST_VALUE | READY_FOR_REVIEW |
| 3 | YouTube | SHORT-01 | FIRST_VALUE | READY_FOR_REVIEW |
| 4 | X | X-03 | FIRST_VALUE | READY_FOR_REVIEW |
| 5 | Facebook | POST-05 | ACTIVATED | READY_FOR_REVIEW |
| 6 | Telegram | TG-01 | FIRST_VALUE | READY_FOR_REVIEW, no enviado |
| 7 | Instagram | POST-02 | Confianza en SHARK | READY_FOR_REVIEW |

No se ha creado contenido deportivo de actualidad sin fuente. Las tres piezas de actualidad permanecen `BLOCKED_BY_SOURCE`.

## Aprobación editorial

Founder Center permite `APROBAR`, `EDITAR`, `DESCARTAR` y `POSPONER`. Todas las decisiones se guardan en `growth_content_reviews`, un espacio propio que no modifica usuarios, picks, membresías ni pagos.

`APROBAR` significa aprobación editorial. Siempre conserva `publication_state=NOT_PUBLISHED`. No existe acción de publicar en este flujo.

## Observabilidad de primeros usuarios

Los hitos reales son:

1. Primer visitante atribuible tras registro.
2. Primer registro real.
3. Primer FIRST_VALUE real.
4. Primer ACTIVATED real.
5. Primer RETURNING real.
6. Primer PREMIUM_INTENT real.
7. Primer PRO real.
8. Primer ELITE real.
9. Primer MRR real.

La navegación anónima no se persiste sin consentimiento. Por ello, “primer visitante real” significa una landing atribuida y confirmada cuando la persona se registra; no se inventa un contador anónimo.

## Feedback

Se reutiliza Beta Program. Las cinco preguntas son opcionales y se muestran después de FIRST_VALUE:

- ¿Entendiste qué hace NeMeSiS?
- ¿Encontraste un partido fácilmente?
- ¿Entendiste SHARK?
- ¿Qué te faltó?
- ¿Volverías mañana?

## SEO y búsqueda orgánica

Localmente están presentes robots, sitemap, canonical, titles, descriptions, Open Graph, structured data e internal linking. La indexabilidad real permanece bloqueada hasta despliegue y observación.

Google Search Console requiere acción humana: verificar dominio por DNS, enviar `/sitemap.xml` e inspeccionar `/landing`, `/calendar`, `/shark` y `/precios`. No se conectó ninguna cuenta.

## Primer cliente de pago

Estado: **BLOCKED_UNTIL_CERTIFIED**.

Falta exactamente:

1. Claves y Price IDs de Stripe certificados en modo seguro.
2. Webhook firmado y persistencia del resultado certificados.
3. Checkout, retorno, cancelación y recuperación probados de extremo a extremo.
4. Renovación, términos y soporte revisados.
5. Una compra de prueba controlada con evidencia sanitizada.

No se ha cobrado nada.

## Paid Ads

`META_FIRST100_TEST` y `GOOGLE_FIRST100_TEST` permanecen `READY_NOT_ACTIVE`, con gasto 0.

No considerar activación hasta disponer de tráfico real, registros reales, FIRST_VALUE real, ACTIVATED real y landing medible en producción. Después seguirá siendo necesaria aprobación explícita de presupuesto y compliance.

## Automatización permitida

Continuous Evolution puede observar, analizar y preparar oportunidades de contenido, SEO, funnel, canal y experimento. No publica, no envía, no gasta y no cobra.

## QA

- `py_compile`: PASS.
- `compileall`: PASS.
- `pytest` completo: 232 PASS.
- Pruebas Growth y Continuous Evolution: 26 PASS.
- Jinja: 198 plantillas PASS.
- Check Growth endurecido: PASS LOCAL.
- Sentinel: 10.0/10, 0 incidencias; 797 rutas y 1.098 enlaces, 0 rotos.
- Privacy Guard y Secret Guard: 1.079 archivos, 0 secretos, 0 incidencias de privacidad.
- Imports y rutas: PASS; 738 rutas analizadas, 0 plantillas o estáticos ausentes.
- Smoke: 29 rutas, 0 fallos y 0 respuestas 500.
- Browser QA del producto: 111 comprobaciones, media 100/100, 0 fallos.
- Browser QA Founder Center: escritorio, tableta y móvil PASS; 0 errores JS, 0 overflow y 0 llamadas externas.
- `git diff --check`: PASS; solo avisos informativos CRLF de Windows.
- Llamadas externas: 0.
- Telegram: 0.
- Stripe: 0.
- Gasto: 0.
- Publicaciones: 0.

Toda la QA utilizó almacenamiento temporal o modo local controlado. Los eventos del recorrido completo están etiquetados `SIMULATED_QA` y no cuentan como negocio real.
## Riesgos y siguiente acción

Riesgo principal: compartir enlaces antes de que el código llegue a producción produciría métricas incompletas o no comparables.

Siguiente acción única: autorizar por separado el push y el despliegue controlados del commit local. Después se repetirá el recorrido en producción y solo entonces se enviará una invitación manual a una persona adecuada.