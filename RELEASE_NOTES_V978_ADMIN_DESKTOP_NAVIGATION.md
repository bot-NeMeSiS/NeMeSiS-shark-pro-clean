# V978 — Navegación del administrador en PC

## Problema y resultado

La revisión del 22 de octubre de 2026 reprodujo fallos del administrador completo
con cuentas sintéticas y almacenamiento LOCAL SAFE:

- En ventanas de 981–1180 px coexistían una barra lateral de 210 px, textos ocultos
  y desplazamientos de cabecera/contenido procedentes de diseños anteriores. A
  1024 px, cabecera y contenido empezaban en 82 px y quedaban tapados por el menú.
- Entre 801 y 980 px, los cinco destinos del menú compacto se distribuían en filas
  dentro de una barra de una sola fila. Desde 901 px persistía además un margen
  reservado al menú lateral, aunque este ya estaba oculto.
- La rueda sobre el espacio entre enlaces desplazaba la página en lugar del menú.
- La entrada habitual `/admin/control-center` no marcaba el Centro de mando como
  ubicación actual.

La corrección unifica la anchura lateral mediante el token existente y da a las
reglas canónicas del admin autoridad sobre la geometría heredada. Mantiene los
nombres visibles en escritorio, adapta conjuntamente menú y contenido, restaura
los eventos del área desplazable y reutiliza el contrato de navegación para el
alias y el menú compacto. La barra superior compacta no reserva el área segura
inferior del dispositivo. El bundle CSS se regenera desde sus fuentes y cambia
su URL versionada para cargar el ajuste.

## Verificación local

| Comprobación | Resultado |
|---|---|
| Admin, navegación, contratos y rutas HTTP seleccionadas | 264 pruebas, cero fallos, errores o saltos |
| Área segura inferior de 34 px, a 390 y 900 px | 2 pruebas adicionales, cero fallos, errores o saltos |
| Recorridos HTTP completos con scripts reales | 30 recorridos de público, cliente y admin; sin errores JS ni POST de navegación |
| Geometría autenticada | 13 tamaños entre 390 y 1920 px; sin desbordamiento horizontal |
| Escritorio desde 981 px | Sidebar, cabecera y main alineados en 210 px; etiquetas visibles |
| Ventanas hasta 980 px | Main sin margen lateral residual; cinco destinos en una sola fila |
| Portátil de 1366×650 | La rueda sobre los huecos desplaza el menú; la página conserva su posición |
| Artefactos | Bundle CSS reproducible y tres autoridades de versión coincidentes |

Las regresiones conservan la comprobación de clic real en el buscador, recorrido
con Tab hasta los últimos destinos y destino activo único. La navegación HTTP
también comprueba Ctrl+K, Escape, continuidad de sesión y respeto del diálogo de
acciones del administrador.

La evidencia es local y sintética; no certifica una sesión administrativa del
propietario en producción. La publicación requiere los checks del candidato y
comprobar el SHA servido por el despliegue automático existente.

## Continuidad del proyecto

Se registra en `project_control/MASTER_CONTROL.md` el **8 de mayo de 2026** como
inicio real, por confirmación expresa del propietario. `project_control/ROADMAP.md`
recoge la dirección de consolidación hacia V1000, con criterios de cierre y
separación entre capacidades implementadas y evidencia de uso/negocio pendiente.

Este cambio afecta a navegación y presentación. El incremento de versión en
`app.py` no modifica lógica de datos, permisos, cobros, envíos ni tareas programadas.
