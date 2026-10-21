# V964 — Saltos del índice del calendario

El índice de competiciones y las secciones agrupadas por país o torneo internacional ahora comparten los mismos identificadores de ancla. Antes, el índice se generaba a partir de una lista mientras la pantalla renderizaba copias agrupadas, así que algunos enlaces cambiaban el hash pero no llevaban a una competición.

La corrección conserva el orden y las agrupaciones existentes. Se valida que todos los enlaces apunten a una sección renderizada en HTML, sin depender de JavaScript ni cambiar partidos o llamadas de proveedor.
