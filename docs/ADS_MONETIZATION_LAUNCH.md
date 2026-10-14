# Publicidad directa de NeMeSiS SHARK PRO

## Estado de este cambio

Este módulo prepara campañas vendidas directamente por NeMeSiS. No utiliza una red publicitaria externa ni comparte datos personales con anunciantes. La campaña solo aparece en superficies de usuarios FREE; el anuncio está etiquetado como publicidad patrocinada. PRO y ELITE no reciben estos anuncios.

## Paquetes iniciales

- 7 días: 49 EUR de precio base.
- 30 días: 149 EUR de precio base.
- 90 días: 349 EUR de precio base.

Los precios son una propuesta comercial inicial, no una promesa de alcance. No se garantizan impresiones, clics, conversiones ni ventas. El checkout activa Stripe Tax automáticamente; si Stripe Tax no está disponible o no está configurado, el sistema debe fallar cerrado y no cobrar. Antes de producción, confirmar con asesoría fiscal la configuración de IVA, datos del emisor, factura y conservación de registros.

## Flujo de contratación

1. El anunciante presenta contacto, empresa/facturación, titular, texto, URL HTTPS y duración.
2. La solicitud se guarda como pendiente de pago. Si falta `STRIPE_SECRET_KEY`, no se realiza ningún cargo y la solicitud queda como `awaiting_payment_setup`.
3. Si Stripe está configurado, se crea un Checkout de pago único en EUR con dirección de facturación, recogida de NIF/IVA y cálculo automático de impuestos. El pago debe verificarse consultando el Checkout Session en Stripe; el navegador por sí solo nunca marca un pago como pagado.
4. El retorno de Checkout confirma el pago solo si coinciden ID de sesión, metadatos, moneda, estado y subtotal.
5. El panel `/admin/ads` permite reconciliar sesiones pendientes contra Stripe. Es útil si el comprador paga y no vuelve a la página.
6. Una campaña pagada queda en `paid_pending_review`; un administrador debe revisar la creatividad y activar manualmente. Si se rechaza, pasa a `refund_required`: tramita el reembolso en Stripe Dashboard y marca `refunded` solo después de verificarlo. No se sirve publicidad pendiente, impagada, pausada, rechazada o caducada.
7. El periodo contratado empieza cuando la campaña se aprueba y activa. Las impresiones y clics son contadores agregados con deduplicación por sesión/día; no se recopilan perfiles publicitarios.

## Operación

- Portal de anunciantes: `/publicidad`.
- Administración privada: `/admin/ads`.
- Prepara en Render la variable `STRIPE_SECRET_KEY` usando el modo apropiado y configura Stripe Tax, datos fiscales y métodos de pago antes de cobrar.
- No copies secretos a GitHub, tickets, capturas o este documento.
- El MVP verifica pagos al volver del Checkout y permite reconciliar manualmente sesiones pendientes. No depende de un webhook de ads; para operación de mayor volumen, añadir un webhook verificado por firma y una conciliación contable antes de escalar.
- El panel no sustituye la contabilidad ni la emisión/archivo de facturas fiscales. Checkout solicita creación de factura; confirmar en modo de prueba que la cuenta Stripe genera una factura válida con los datos fiscales requeridos antes de vender campañas. Los reembolsos se ejecutan manualmente en Stripe y se registran en el panel tras verificar el resultado.
- No se admiten anuncios de apuestas, casinos, tipsters, promesas de beneficios, productos ilegales u otras categorías restringidas. Toda creatividad requiere revisión humana.

## Puesta en marcha segura

1. Revisar PR y ejecutar todos los controles CI.
2. Probar en Stripe test mode con impuestos de prueba; verificar rechazo de pagos no confirmados, importes manipulados y URLs no HTTPS.
3. Confirmar que FREE ve el anuncio y PRO/ELITE no.
4. Confirmar contadores, pausa, caducidad y que una campaña impagada no se sirve.
5. Confirmar la factura y tratamiento de IVA con un asesor.
6. Solo después, configurar credenciales live en Render y hacer una compra real pequeña autorizada por el titular. No activar campañas reales antes de la revisión de contenido.
