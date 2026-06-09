# V704 DATA EXPANSION + REAL SPORTS COVERAGE REPORT

## Resumen ejecutivo

V704 ataca el problema principal detectado tras V703: la aplicacion se veia mas premium, pero podia transmitir poca cobertura si la base tenia mas datos de los que la interfaz o los motores estaban mostrando.

No se han inventado partidos, picks ni cuotas. Los cambios amplian el uso de datos reales ya disponibles o configurables mediante fuentes existentes: SQLite, SportsDB, The Odds API, importaciones legales, picks publicados y recomendaciones SHARK.

## Cambios aplicados

### Cobertura de competiciones

Se ampliaron las competiciones semilla y configuradas para cubrir mas del mapa solicitado:

- Espana: LaLiga, Segunda Division, Copa del Rey, Supercopa de Espana.
- Inglaterra: Premier League, Championship, FA Cup.
- Italia: Serie A, Serie B.
- Alemania: Bundesliga, Bundesliga 2.
- Francia: Ligue 1, Ligue 2.
- Portugal: Primeira Liga.
- Europa: Champions League, Europa League, Conference League, Nations League.
- Internacional: World Cup, Euro, World Cup Qualifiers.
- Sudamerica: Copa Libertadores, Copa Sudamericana, Copa America.

### Mas partidos visibles

Se redujeron recortes artificiales:

- `get_matches()` sube de 150 a 300 partidos por dia/filtro.
- `get_upcoming_matches()` sube de 150 a 300 por defecto.
- Sports Hub ahora puede manejar hasta 200 partidos de hoy, 160 proximos, 120 finalizados, 80 live, 80 con odds y 80 con picks.
- Sports Hub semana consulta 10 dias y hasta 220 partidos.
- Dashboard usa mas picks, combis, resultados y candidatos.

### Picks y recomendaciones

- `pick_candidate_matches()` sube de 24/14 dias a 80/21 dias.
- `smart_pick_board()` sube candidatos hasta 80 y hot picks hasta 12.
- La pagina `/picks` muestra hasta 80 candidatos reales.
- Las recomendaciones se calculan sobre mas partidos proximos, manteniendo filtros de calidad.

### Cuotas

- The Odds API pasa de limite por defecto 80 a 250 eventos por ciclo.
- Se mejoro `v565_extract_odds()` para leer cuotas guardadas como `outcomes`, no solo campos planos `home/draw/away`.
- Esto permite que cuotas ya cacheadas por The Odds API aparezcan en recomendaciones y candidatos.

### SHARK coverage

- Mas partidos candidatos reciben analisis basico SHARK al ampliar ventana y limites.
- Si faltan cuotas, el sistema sigue mostrando estado honesto: esperando cuota.
- No se publican picks reales sin datos suficientes.

### Rendimiento

- Se agrego cache en memoria para `resolve_team()` durante el proceso.
- Esto evita repetir consultas de identidad/escudo para el mismo equipo en listados largos.

### Estabilidad

- Se corrigio un bug real: `annotate_match()` podia leer sesion fuera de request cuando se usaba desde tareas de fondo o auditorias. Ahora usa favoritos vacios si no hay request context.

## Validacion

- `compileall`: OK.
- Smoke test local V704: 29 rutas, 0 errores 500, 0 respuestas 4xx/5xx.
- Tiempo del smoke local: 23.66 segundos.

## Cobertura medida en smoke local

Estos numeros no son datos de produccion. Son datos temporales controlados para validar volumen y renderizado:

- Partidos totales visibles: 16.
- Partidos hoy visibles: 10.
- Partidos live visibles: 2.
- Ligas visibles: 8.
- Picks publicados visibles: 6.
- Candidatos a pick: 12.
- Recomendaciones SHARK: 12.
- Partidos con cuotas reconocidas: 16.
- Deportes/mercados configurados para odds: 14.

## Limitaciones reales detectadas

- No hay acceso en esta sesion a la base persistente real de Render `/data/database.db`.
- No hay red/API real activa para medir partidos reales de SportsDB/Odds en vivo.
- La cobertura real depende de `THESPORTSDB_KEY`, `THE_ODDS_API_KEY`, `ENABLE_ODDS_API`, regiones y mercados configurados.
- Si una competicion no existe o no esta disponible en The Odds API, se registrara error de sync pero no se inventaran datos.
- Cargar muchos equipos en frio puede ser lento si no hay identidades cacheadas; se mitig? con cache en memoria.

## Conclusion

V704 aumenta la capacidad real de cobertura sin falsificar contenido. La app ya no esta limitada por topes pequenos en sus pantallas principales y aprovecha mejor cuotas cacheadas. El siguiente paso real es ejecutar sync en Render con claves reales y medir cobertura de produccion durante varios dias.
