# V927 Desktop Empty Space Guard QA

La capa V927 se aplica al final de la cascada y solo desde 1024 px.

- Padding superior de shells V927: 8 px.
- Hero publico desktop: 340 px.
- Secciones compactas: margen 8 px y padding 12 px.
- Cards KPI: altura minima 86 px; las del resumen lateral de home, 72 px.
- Admin legacy hero y strip historico: ocultos en el dashboard ya modernizado.
- Tablas: overflow horizontal interno, no del viewport.
- Mobile: fuera de la media query V927.

El detector renderizado confirma un solo H1/hero y ausencia de 500 en rutas clave.
