# V928 Client Mobile Reference QA

- Cabecera compacta y bottom navigation fija de cinco accesos.
- Desktop nav oculta; cards apiladas; tablas transformadas; filtros con scroll horizontal.
- Padding inferior usa safe area para evitar contenido inaccesible tras la navegación.
- Botones táctiles, texto sin solapamiento y CTA de estado seguro a ancho completo.
- Viewports con capturas: 390x844 y 430x932.
- Validación adicional real: 360x800, 375x812, 390x844, 393x852, 412x915 y 430x932.
- Resultado adicional: 66 cargas de 11 rutas, 0 errores HTTP y 0 overflow.
- La barra fija aparece sobre la captura full-page porque representa el viewport visible; el contenido conserva padding de scroll seguro.
