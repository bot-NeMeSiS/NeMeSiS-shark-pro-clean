# V852 Picks: Calidad, Ligas Raras y Datos Pasados

## Problema
El vídeo mostraba picks de ligas poco comerciales y fechas antiguas con demasiado protagonismo.

## Corrección
- `engines/picks_quality_engine.py` penaliza competiciones de baja relevancia.
- Se detectan términos como Georgian Erovnuli, Latvian Higher, Finnish Ykkonen/Ykkönen, youth, reserves, regional, amateur y friendly débil.
- Picks pasados se marcan como `Archivado`.
- Picks sin cuota/selección/contexto se marcan como `Pick en revisión`.
- `/picks` muestra primero los picks premium listos y degrada visualmente los demás.

## Estados usados
- Pick activo.
- Pick en revisión.
- Cuotas pendientes.
- Selección pendiente.
- Archivado.
- Liga baja relevancia.

## Check
`tools/check_v852_picks_quality_and_stale_data.py`.
