# V775 Mobile Video Review QA

Problemas observados en el vídeo móvil usado como referencia:

- Pantallas cliente demasiado largas y repetitivas.
- Barra inferior con demasiadas opciones para ancho móvil.
- Filtros, acciones y cards ocupaban demasiada altura.
- En cards de calendario/directo se perdía claridad de ambos equipos.
- El botón SHARK y el teclado podían competir con navegación inferior.
- Páginas Telegram/SHARK seguían con diseño antiguo y enlaces rotos.
- Menú Más era una parrilla sin jerarquía.

Corrección V775:

- Shell móvil compacto.
- Barra inferior de 5 accesos.
- Rails horizontales para acciones/filtros.
- Cards partido con local y visitante visibles.
- SHARK como bottom sheet en móvil.
- Ocultación de nav durante teclado.
- Páginas de cliente reagrupadas por prioridad.
