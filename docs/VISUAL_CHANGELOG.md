# Registro de cambios visuales

## VIS-2026-10-29-01 — presencia de marca por pantalla

**Estado:** propuesta implementada en rama, sin despliegue. El aviso previo se
ha comunicado al fundador en el chat; no equivale a aprobación visual final.
**Base:** main `33d1b85125a887bb47c036844e0f70eb474afc28` (V1000.4).

### Qué cambia y por qué

Recuperar presencia del océano y del tiburón existente sin reintroducir marcas
repetidas ni perder las superficies de lectura opacas. Se reutilizan los tokens
de la escena en la hoja de refinamiento que ya carga la aplicación: ninguna
hoja, imagen, llamada de proveedor o animación nueva.

| Pantalla | Tiburón anterior PC/móvil | Propuesta PC/móvil | Océano propuesto PC/móvil |
|---|---:|---:|---:|
| Inicio `/`, `/app` | .085 / .065 | .30 / .22 | .72 / .62 |
| SHARK `/shark` | .085 / .065 | .34 / .26 | .68 / .60 |
| Acceso cliente y registro | .24 / .24 | .34 / .34 | .70 / .60 |
| Otras pantallas cliente | .085 / .065 | .16 / .12 | .64 / .56 |
| Admin ordinario | .06 / .06 | sin cambio | sin cambio |

Son opacidades CSS del elemento, no porcentajes de mejora ni pruebas de
visibilidad de cada píxel. Admin-login conserva también su cascada anterior.
El océano conserva el oscurecimiento y el tiburón su geometría original. No se
promete verlo a través de tarjetas opacas que ocupen esa zona de una pantalla.

### Qué se conserva

Arte aprobado y hashes, logo, posición/tamaño, una sola escena no interactiva,
colores de texto, controles, paneles opacos, planes/permisos y navegación. Se
mantiene la ocultación de escena en alto contraste, colores forzados o
transparencia reducida. La iluminación opcional conserva su comportamiento.
Se versiona la URL de la hoja existente para no depender de la caché previa.

### Evidencia y límites

`tests/test_brand_presence_profiles.py` comprueba CSS y assets reales en una
composición aislada de Chromium, con 12 combinaciones de ruta/rol y cuatro
anchos, cuatro tiers visuales, paneles/controles opacos, assets, escena única,
interacción y preferencias de accesibilidad. El CSS y los bytes de imágenes del checkout se incrustan en un DOM de muestra;
no se navega por HTTP, no se importa App ni se certifican sesiones/roles reales.
Las capturas de esta composición deben etiquetarse como tales, no como pantallas
reales de la app ni producción. CI y QA de rutas autenticadas sobre el SHA exacto
siguen siendo puertas independientes. No acredita mejoras de velocidad, los 502
ni backup/restauración.

### Reversión

Revertir este ajuste de variables y la versión de URL de
`v1000-client-refinement.css`. No hay migración, datos o imágenes que restaurar.
Las reglas de comunicación permanecen salvo instrucción del fundador.

### Comunicación

Aviso previo: más marca en Inicio/acceso/SHARK, fondo moderado en pantallas de
consulta, Admin sobrio y sin rediseñar tarjetas, logo o animaciones. La entrega
debe indicar PR/SHA, pruebas ejecutadas, pendientes y que todavía no está en la
web publicada. No merge, deploy o auto-merge como consecuencia de este registro.

### Validación local registrada

55 casos únicos PASS en Chromium local: 48 combinaciones de ruta/rol/ancho,
cuatro tiers y tres comprobaciones de assets, caché y comunicación. Se comparan
ocho parejas antes/después; Admin conserva las métricas observadas. No son
55 pruebas funcionales de la plataforma. La primera variante del harness con
un origen HTTP ficticio fue bloqueada por la política del navegador (52 fallos
de navegación, tres pruebas estáticas aprobadas). Se conservó ese resultado y
se pasó a composición DOM sin HTTP, sin modificar la política ni controles.
La revisión de capturas detectó un recorte del contenedor de muestra, que se
corrigió en el harness y se añadió como aserción; no fue un cambio del producto.
La suite completa/App no se ejecutó localmente porque falta Flask.
