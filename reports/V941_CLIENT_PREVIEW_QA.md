# V941 · Vista cliente protegida

## Alcance
/admin/client-preview y /admin/client-preview/frame permiten Inicio, Partidos, Directo, Picks, SHARK, Telegram, Perfil y Membresías. FREE/PRO/ELITE se seleccionan sin cambiar la sesión principal. El centro ofrece móvil390, tablet768 y PC1440; también abre la vista completa.

Se reutilizan tarjetas, perfil, planes, cabeceras y políticas de membresía canónicas. Deporte y picks proceden de la lectura Sports Truth existente, limitados a doce tarjetas por vista; esta muestra no certifica cobertura de calendario completa. Los picks se filtran por membership_required y el plan simulado. Los ajustes de banner/highlights se aplican a la presentación.

SHARK, Telegram, Perfil y Membresías reutilizan componentes dentro de una presentación segura: chat, compra, códigos de vinculación, contraseña y cambios de cuenta están desactivados. No se cargan datos personales. Los precios de pago se indican como no consultados; no se inventan precios ni disponibilidad de checkout. Esto no es una réplica interactiva de todos los handlers de cliente.

## Pruebas
- 24 escenarios HTTP: ocho pantallas por tres planes. Sesión exactamente igual antes/después y filas completas de usuarios intactas.
- 24 escenarios Chromium con el HTML real del endpoint: cuatro pantallas (SHARK, Telegram, Perfil, Membresías), tres planes, anchos390/1440.
- 12 verificaciones de enlaces reales: cada destino permanece dentro de preview y conserva el perfil.
- Selectores móvil/tablet/PC, sandbox, enlace de apertura y geometría también ejercitados en la suite Admin.
- Sin desbordamiento del documento, errores JavaScript ni solicitudes externas en los casos de navegador.
- Acceso anónimo protegido, planes/páginas no permitidos rechazados, POST a preview rechazado, no-store y CSP comprobados.
- Pruebas adicionales de clientes autenticados recorren ocho rutas reales con FREE/PRO/ELITE en base desechable.

## Evidencia e inspección
Capturas reales: data/local_dev/admin-master-v941-qa/preview-{shark,telegram,profile,memberships}-{free,pro,elite}-{390,1440}.png.
XML de navegador: candidate-b6df8cebce124b14b9b7ef834aae3815/result.xml; enlaces: candidate-a621caa622174afaafc2131da512084b/result.xml, ambos bajo data/local_dev.
Se inspeccionaron Perfil FREE390, SHARK PRO1440 y Membresías PRO1440, además del centro Admin390/1440. No se declara pixel-perfect, Safari ni dispositivos físicos. Las capturas están rotuladas SIMULATED_QA y no representan cuentas de clientes reales.
