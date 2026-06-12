# V741 Calendar Experience QA Report

## Resultado

`CALENDARIO_PREMIUM_LISTO` — Score 100/100 en validación estática.

## Puntos revisados

- Pantalla de calendario central presente.
- Buscador principal presente.
- Rail de días presente.
- Rail de ligas presente.
- Agrupación por día presente.
- Tarjetas premium de partido presentes.
- Escudos/fallbacks presentes.
- Estado vacío claro presente.
- CSS anti-solape presente.
- CSS mobile-safe presente.
- API calendar enriquecida presente.
- Alias `/partidos` presente.

## Criterio de calidad

La pantalla debe permitir al cliente encontrar un partido sin abrir varias secciones:

1. Elegir día o periodo.
2. Buscar por equipo o liga.
3. Filtrar por liga/país/pick/directo.
4. Ver partido con hora Madrid, escudos, competición en castellano y estado.
5. Entrar al detalle del partido.

## Nota

La QA visual definitiva debe hacerse en móvil real y Render real con datos de producción sincronizados.
