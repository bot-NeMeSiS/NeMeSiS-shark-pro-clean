# NeMeSiS SHARK PRO V521

FINAL PRODUCT CLEANUP REAL DATA UX PASS

## Enfoque

V521 limpia la experiencia final de cliente sin rehacer la arquitectura. Mantiene login, roles, admin, Telegram, SportsDB, SQLite persistente y rutas actuales.

## Cambios principales

- Limpieza de partidos con nombres falsos en el arranque y en las lecturas de partidos.
- Seed centrado en 24 equipos reales principales.
- Match Hub y Live con estados premium, escudos seguros y estados vacios elegantes.
- Picks, combinadas y favoritos sin enlaces visibles a APIs para cliente.
- Navegacion cliente reducida a Inicio, Partidos, Live, Picks, Favoritos y Perfil.
- Navegacion admin separada con Usuarios, SportsDB Sync, Telegram, Import Center y Sistema.
- Escudos reforzados con aliases, external_id, resolucion por nombre y cache persistente.
- Nueva vista admin de sistema en `/admin/system` para evitar enlazar el menu a JSON crudo.

## Datos falsos bloqueados

Se filtran y eliminan nombres como Premier Home, Premier Away, Equipo Champions A, Seleccion Local, Club LaLiga Local y Club LaLiga Visitante.

## Render

Mantiene `DB_PATH=/data/database.db`.

No incluye scraping ilegal ni datos demo presentados como reales.
