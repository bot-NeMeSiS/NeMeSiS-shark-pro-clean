# V634_RESPONSIVE_CLIENT_POLISH

Build preparado sobre la base V633 para mejorar experiencia cliente en móvil y web.

## Cambios principales

- Versión actualizada a `V634_RESPONSIVE_CLIENT_POLISH` en `app.py` y `VERSION.txt`.
- Navegación cliente con acceso visible a **Combis** en desktop y barra inferior móvil.
- Favoritos tipo app deportiva: estrella `☆/★` añadida en filas de calendario, live y Sports Hub.
- Nuevo endpoint seguro `POST /api/favorites/toggle` para añadir/quitar favoritos sin formularios manuales.
- Calendario con encabezado más corto y compacto.
- Calendario con sección extendida de **Próximos días**, agrupada por día y liga.
- Días del calendario en español desde backend: Lunes, Martes, Miércoles, Jueves, Viernes, Sábado, Domingo.
- Live con copy más directo y menos explicaciones largas.
- CSS responsive V634 para móvil y web:
  - títulos más contenidos,
  - menos padding,
  - tarjetas deportivas más compactas,
  - filas de partido más tipo Flashscore/Sofascore,
  - botón SHARK flotante más pequeño en móvil,
  - barra inferior desplazable para evitar botones comprimidos,
  - combis más visibles.

## Archivos tocados

- `app.py`
- `VERSION.txt`
- `templates/base.html`
- `templates/calendar.html`
- `templates/live.html`
- `templates/sports_hub.html`
- `static/app.css`

## Validación

- `python3 -m compileall app.py engines database_manager.py services`: OK.
- Búsqueda de weekdays ingleses visibles: OK.
- ZIP limpio generado sin `.git`, `.venv`, `__pycache__`, DB local, logs ni ZIPs internos.

## Pendiente real

- Revisión visual en Render/móvil real con datos abundantes para ajustar microespaciados si hiciera falta.
- No se ejecutó Flask test client porque el entorno no tiene Flask instalado.
