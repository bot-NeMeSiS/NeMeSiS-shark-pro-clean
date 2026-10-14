# Publicidad directa de NeMeSiS SHARK PRO

## Estado de este cambio

Este módulo prepara campañas vendidas directamente por NeMeSiS. No utiliza una red publicitaria externa ni comparte datos personales con anunciantes. La campaña solo aparece en superficies de usuarios FREE; el anuncio está etiquetado como publicidad patrocinada. PRO y ELITE no reciben estos anuncios.

## Paquetes iniciales

- 7 días: 49 EUR de precio base.
- 30 días: 149 EUR de precio base.
- 90 días: 349 EUR de precio base.

Los precios son una propuesta comercial inicial, no una promesa de alcance. No se garantizan impresiones, clics, conversiones ni ventas. El checkout activa Stripe Tax automáticamente, pero Stripe solo calcula impuestos donde existe una inscripción activa. Si Stripe Tax no está disponible o no se ha verificado una inscripción activa y el código fiscal correcto, el sistema debe fallar cerrado y no cobrar. No establezcas `ADS_STRIPE_TAX_READY=true` hasta confirmarlo en el Dashboard y con tu asesor fiscal. `ADS_STRIPE_TAX_CODE` debe contener el código de producto exacto elegido con asesoría fiscal; no uses un código genérico inventado. Antes de producción, confirmar con asesoría fiscal la configuración de IVA, datos del emisor, factura y conservación de registros.

## Flujo de contratación

1. El anunciante presenta contacto, empresa/facturación, titular, texto, URL HTTPS y duración.
2. La solicitud se guarda como pendiente de pago. Si falta `STRIPE_SECRET_KEY`, `STRIPE_ADS_WEBHOOK_SECRET` o `ADS_STRIPE_TAX_READY` no es `true`, no se realiza ningún cargo y la solicitud queda como `awaiting_payment_setup`.
3. Si Stripe y la preparación fiscal están verificados, se crea un Checkout de pago único en EUR con recogida de datos fiscales, impuestos automáticos y solicitud de factura. El pago se confirma mediante webhook firmado y también puede reconciliarse consultando el Checkout Session desde el servidor; el navegador por sí solo nunca marca un pago como pagado.
4. El webhook firmado confirma el pago solo si coinciden ID de sesión, metadatos, moneda, estado y subtotal. La página de retorno solo ofrece confirmación secundaria al cliente; nunca es la única fuente de verdad.
5. El panel `/admin/ads` permite reconciliar sesiones pendientes contra Stripe. Es útil si el comprador paga y no vuelve a la página.
6. Una campaña pagada queda en `paid_pending_review`; un administrador debe revisar la creatividad y activar manualmente. Si se rechaza, pasa a `refund_required`: tramita el reembolso en Stripe Dashboard y marca `refunded` solo después de verificarlo. No se sirve publicidad pendiente, impagada, pausada, rechazada o caducada.
7. El periodo contratado empieza cuando la campaña se aprueba y activa. Las impresiones y clics son contadores agregados con deduplicación por sesión/día; no se recopilan perfiles publicitarios.

## Operación

- Portal de anunciantes: `/publicidad`.
- Administración privada: `/admin/ads`.
- Prepara en Render `STRIPE_SECRET_KEY` y `STRIPE_ADS_WEBHOOK_SECRET`. Configura en Stripe el endpoint `https://bot-apuestas-crgf.onrender.com/api/stripe/ads-webhook` para `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed` y `checkout.session.expired`.
- Configura `ADS_STRIPE_TAX_CODE` con el código de producto exacto acordado con tu asesor fiscal y establece `ADS_STRIPE_TAX_READY=true` solo después de verificar la configuración de Stripe Tax, una inscripción activa en la jurisdicción que corresponda y ese código fiscal. Stripe puede cobrar cero impuestos sin error cuando no hay una inscripción activa; consulta [Stripe Tax](https://docs.stripe.com/tax/checkout.md) y a tu asesor fiscal.
- No copies secretos a GitHub, tickets, capturas o este documento.
- El webhook firmado es obligatorio y procesa finalización, pagos asíncronos y expiración/fallo de Checkout. La página de retorno es solo UX; la conciliación manual en `/admin/ads` es una salvaguarda secundaria.
- El panel no sustituye la contabilidad ni la emisión/archivo de facturas fiscales. Checkout solicita creación de factura; confirmar en modo de prueba que la cuenta Stripe genera una factura válida con los datos fiscales requeridos antes de vender campañas. Los reembolsos se ejecutan manualmente en Stripe y se registran en el panel tras verificar el resultado.
- No se admiten anuncios de apuestas, casinos, tipsters, promesas de beneficios, productos ilegales u otras categorías restringidas. Toda creatividad requiere revisión humana.

## Puesta en marcha segura

1. Revisar PR y ejecutar todos los controles CI.
2. En un entorno de prueba, configurar un webhook independiente y verificar la firma usando `STRIPE_ADS_WEBHOOK_SECRET`. No reutilices automáticamente el secreto de otra URL de webhook.
3. En Stripe Dashboard, verificar Tax Settings, inscripción activa y código fiscal del producto; no marques la variable de readiness hasta confirmarlo.
4. Probar en Stripe test mode con impuestos de prueba; verificar rechazo de pagos no confirmados, importes manipulados y URLs no HTTPS.
5. Confirmar que FREE ve el anuncio y PRO/ELITE no.
6. Confirmar contadores, pausa, caducidad y que una campaña impagada no se sirve.
7. Confirmar la factura y tratamiento de IVA con un asesor.
8. Solo después, configurar credenciales live en Render y hacer una compra real pequeña autorizada por el titular. No activar campañas reales antes de la revisión de contenido.
