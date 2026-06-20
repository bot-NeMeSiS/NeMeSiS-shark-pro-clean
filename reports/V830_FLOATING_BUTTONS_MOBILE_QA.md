# V830 Floating Buttons Mobile QA

## Botón flecha arriba

Se identificó el botón `ns-scroll-top` en `templates/base.html`. En móvil no aporta valor suficiente frente al coste visual: aparece como un botón suelto y compite con la bottom nav y el floating SHARK.

Decisión V830: ocultarlo en móvil mediante CSS. En desktop puede seguir existiendo si el layout lo necesita.

## Floating SHARK

Se mantiene como identidad cliente, pero con reglas más estrictas:

- Solo cliente, nunca admin.
- Oculto en `/shark`, `/shark-ai` y `/shark-core`.
- Reubicado por encima de la barra inferior.
- Tamaño móvil de 50px para no tapar contenido.
- Panel SHARK abierto con bottom seguro por encima de la navegación.

## Riesgo eliminado

La zona inferior móvil ya no tiene tres elementos compitiendo por el mismo espacio. La prioridad visual queda así:

1. Bottom nav centrada.
2. Floating SHARK por encima.
3. Scroll-to-top oculto en móvil.
