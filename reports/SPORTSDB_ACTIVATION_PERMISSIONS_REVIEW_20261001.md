# TheSportsDB: activación operativa y permisos de contenido

Revisión: 01/10/2026. Base: `19ce7ad3b7d75d0fdb678794aca793535e5b0048`.
No es un dictamen jurídico, una verificación de facturación ni una certificación de todos los contenidos de producción.

## Conclusión

La casilla antigua mezclaba activar consultas con declarar comprobaciones legales y de cuenta. Se sustituye por una solicitud operativa explícita, sin marcar automáticamente. Se mantienen administrador, CSRF, fuente seleccionada y confirmación; no se amplían permisos de publicación.

Las condiciones de TheSportsDB contemplan aplicaciones y servicios mediante sus endpoints, límites y atribución. Reservan derechos de terceros y restringen revender la API [1]. Usar datos en la aplicación no equivale a poder publicar cualquier vídeo o imagen. Las condiciones de Creative Commons dependen de la licencia concreta, no de un indicador booleano [4].

La lectura cacheada de [1] mostró fecha 01/07/2025; la versión indexada de la misma página mostró 17/09/2026 y explicaciones adicionales sobre imágenes. Se documenta esa diferencia. La ayuda utiliza los puntos concordantes y no acredita qué versión contractual aceptó el titular.

## Cambios de esta propuesta

1. Ayuda desplegable dentro del panel existente con alcance, fuentes oficiales y fecha de revisión. Aclara que facturación y licencias individuales no están verificadas.
2. Confirmación «Quiero activar las consultas…» en lugar de «He verificado que la cuenta…». No es un descargo que legalice usos no permitidos.
3. La revisión de un vídeo rechaza páginas generales de TheSportsDB como evidencia de derechos: documentación, precios, cuenta, endpoints y ficha del evento. Es un filtro negativo limitado, no un verificador de licencias. Otras URL siguen requiriendo fundamento y revisión humana documentada. Bloquear o mantener pendiente no requiere inventar permisos.
4. La ficha mantiene valores, referencia y fecha de estadísticas y acredita TheSportsDB solo cuando es la fuente observada.
5. Se corrige el texto de consumo manual: hasta 12 consultas por ejecución; ese recolector no comparte el presupuesto diario inicial de 60 del módulo pospartido.

No se cambia Cron, cuenta, plan, claves, usuarios, pagos ni activación persistente. No se revisan ni revocan autorizaciones antiguas automáticamente. No se añade otro trabajador o panel. El control de publicación APP-only permanece.

## Pendientes que no deben darse por resueltos

**Enlaces:** GS Media exige valorar conocimiento y finalidad lucrativa al enlazar publicaciones no autorizadas [3]. Solo enlazar no es una garantía universal. Tampoco todo enlace lícito requiere necesariamente una nueva licencia: nuestra revisión por elemento es una política conservadora, no una descripción exhaustiva de la ley.

**Privacidad:** el reproductor tras clic limita la carga automática en ese recorrido; no acredita cumplimiento completo. La AEPD contempla consentimiento antes de servicios con cookies no necesarias, y el artículo 22.2 LSSI prevé información/consentimiento y excepciones [5][6]. Falta inspeccionar red real, miniaturas, rechazo/retirada y políticas.

**Imágenes y marcas:** no se ha completado un inventario global de escudos, fotografías y binarios servidos por rutas históricas, Telegram, SEO o marketing. Registrar recurso, fuente, autor, licencia, canal y evidencia. Una marca CC o apariencia oficial no bastan [1][4].

**Datos comerciales:** no se da por autorizada una venta futura de datasets/exportaciones del proveedor. Debe aclararse su alcance con el proveedor, separado de mostrar estadísticas y análisis propios en la app.

**Negocio:** esta revisión no certifica fiscalidad del titular, contratación de membresías, consumo, tratamiento de datos personales o publicidad/afiliación de apuestas. La comprobación jurídica integral y los permisos de contenido no se sustituyen por pruebas de software.

## Consulta preparada para TheSportsDB (borrador, NO enviada)

Asunto: Alcance de Premium para una aplicación española de análisis deportivo

En NeMeSiS SHARK PRO queremos mostrar calendario, resultados y estadísticas con atribución, usando endpoints oficiales y caché de servidor. El producto ofrece acceso gratuito y membresías de análisis, sin dar acceso a vuestra clave ni revender vuestra API.

Solicitamos confirmación escrita para: uso de datos en este producto comercial; conservación histórica y análisis derivados; documentación de derechos de imágenes/escudos concretos; y procedencia/autorización de enlaces de highlights, límites territoriales y de inserción. No interpretamos Premium como autorización automática de vídeos. No adjuntamos claves ni contraseñas.

## Evidencia técnica

40 pruebas nuevas correctas localmente, con SQLite temporal y conexiones externas bloqueadas. Se verifican rechazo de evidencia genérica sin escrituras, conservación del bloqueo de vídeos tras activar consultas, revisión APP-only y textos/atribución. Se comprobaron los blobs de los cuatro archivos editados contra main antes de modificarlos.

La suite completa Flask/navegador y el despliegue deben verificarse sobre el HEAD publicado. No se certifican por este resultado local ni se afirma activación en producción. Los resultados posteriores se anotan en la PR.

## Fuentes primarias consultadas

[1] TheSportsDB, Terms of use: https://www.thesportsdb.com/docs_terms_of_use.php
[2] TheSportsDB, documentación: https://www.thesportsdb.com/documentation
[3] TJUE, GS Media C-160/15, comunicado de la sentencia: https://curia.europa.eu/jcms/upload/docs/application/pdf/2016-09/cp160092es.pdf
[4] Creative Commons, licencias: https://creativecommons.org/cc-licenses/
[5] AEPD, Guía de cookies, mayo 2024, apartado 3.2.3: https://www.aepd.es/guias/guia-cookies.pdf
[6] BOE, Ley 34/2002, artículo 22.2: https://www.boe.es/buscar/act.php?id=BOE-A-2002-13758
