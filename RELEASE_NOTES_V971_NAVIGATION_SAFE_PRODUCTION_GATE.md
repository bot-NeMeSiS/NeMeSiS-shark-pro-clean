# V971 — Validación de navegador resistente a navegación simultánea

El control de publicación de producción captura fallos de carga de imágenes por documento. Durante un recorrido móvil, Playwright puede destruir el contexto del documento entre la comprobación de la URL y la lectura del DOM. Ahora espera a que el documento siguiente alcance `DOMContentLoaded` y repite esa lectura una vez únicamente ante ese error concreto.

Los demás errores del navegador siguen fallando el control. La captura mantiene el identificador y la URL del documento que finalmente observó; no convierte una navegación incompleta en una validación satisfactoria. Esta versión mejora la fiabilidad de la certificación posterior al despliegue sin modificar datos, rutas de usuario ni llamadas a proveedores.

Validación: pruebas unitarias de reintento y propagación de errores ajenos, suite de regresión de imágenes con Playwright en navegador local y comprobación de navegación HTTP simulada. El despliegue de V970 fue verificado aparte; esta corrección requiere los controles CI y la certificación de su propio SHA antes de considerarse publicada.
