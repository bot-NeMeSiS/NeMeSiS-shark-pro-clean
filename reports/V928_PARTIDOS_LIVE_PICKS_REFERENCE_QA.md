# V928 Partidos, Live y Picks Reference QA

- Partidos: filtros por horizonte, liga y país; hora Madrid; grupos y cards desde cache/DB.
- Live: todos/en directo/descanso/finalizados/con pick; marcador y minuto solo si existen.
- Picks: destacados/activos/cerrados/conservadores/valor; puerta de publicación real.
- Gate de pick: partido, mercado, selección y cuota válida obligatorios.
- Contextos safe exponen fuente, proveedor, cache, última sincronización y `no_render_api_call=true`.
- Render de página no obliga llamadas externas.
- Estado probado con DB temporal vacía: 0 partidos, 0 live y 0 picks; UI operativa y explicativa.
- Capturas actualizadas tras corregir compresión de filtros y labels de proveedor.
- No se inventaron partidos, cuotas, resultados, minutos ni picks.
