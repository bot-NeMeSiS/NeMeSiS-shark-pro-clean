# V962 — Calendario móvil más compacto

Las tarjetas completas del calendario en móvil ajustan sus filas al contenido real. Antes, algunas tarjetas dejaban hueco bajo los equipos y comprimían la fila de acciones; ahora la distribución respeta los nombres y el espacio real del botón. Cuando los equipos caben en 28 px, se ahorran hasta 17 px por partido; horas y nombres largos conservan la altura que necesitan. Nombres, hora, marcador, estado, escudos y enlaces se mantienen, y la fila de acciones conserva el área táctil de 44 px.

La mejora se limita a tarjetas completas del calendario en anchuras móviles. No cambia la agenda, los datos deportivos, permisos ni llamadas a proveedores.

Validación visual de solo lectura a 390 px: 240 tarjetas completas, 690 px menos de altura acumulada en la muestra cargada; un ejemplo pasó de 102 a 85 px. Validación adicional: recorridos de calendario en español, inglés y francés; JavaScript activado y desactivado; escritorio, móvil estrecho y móvil estándar; navegación GET, filas sin recortes y ausencia de desbordamiento horizontal.
