# V937 Diamond Logos And Backgrounds

## Problema demostrado

`base.html` montaba `ns-ambient`, `v825-shark-background`, `v815-client-shark-backdrop`, `v810-big-shark-decoration`, `membership-energy-bar` y `ns-route-glow`. V933 los ocultaba, pero seguían en cada DOM. Además, V936 reemplazaba el tiburón de la Home por un orbe radial invisible detrás del contenido.

## Corrección

- Retirado el markup heredado, sin borrar sus estilos de compatibilidad.
- Eliminado el orbe radial de Home.
- Restaurada una única firma SHARK punteada, con máscara SVG, opacidad controlada y `pointer-events:none`.
- Ajuste específico móvil para evitar texto tapado o scroll horizontal.
- El isotipo sigue enlazado y conserva proporción, nitidez y contraste.

## Resultado

Máximo una gran decoración SHARK por pantalla. No hay doble logo, tiburón flotante dentro de SHARK, fondo cliente dentro de admin ni capas superpuestas. La comparación final no detectó overflow en ningún perfil.
