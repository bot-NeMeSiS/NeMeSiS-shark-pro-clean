# NeMeSiS SHARK PRO — README Master

> Control operativo vigente: [MASTER_CONTROL](project_control/MASTER_CONTROL.md).
> Las versiones y afirmaciones inferiores son contexto historico. No prueban
> el estado actual, autorizaciones ni los tiers realmente configurados.

## Estado

Versión de código actual: V952 Timeline Data Provenance. La presencia de esta
versión en el repositorio no prueba que esté desplegada; producción se confirma con
el SHA y el estado del runtime de Render.

NeMeSiS SHARK PRO es una plataforma Flask premium para fútbol, picks, recomendaciones SHARK, favoritos, Telegram, membresías FREE/PRO/ELITE y administración protegida.

## Stack

- Flask
- SQLite
- Gunicorn
- Render
- Jinja templates

## Render

La configuración principal vive en `render.yaml`.

Variable crítica:

```text
DB_PATH=/data/database.db
```

No borrar la base de datos en producción. Las migraciones son seguras e incrementales.

## Estructura

- `app.py`: aplicación principal, rutas, migraciones, scheduler y APIs.
- `engines/`: lógica interna reutilizable.
- `templates/`: vistas cliente/admin.
- `static/`: estilos y assets.
- `docs/`: documentación histórica V5XX.
- `database_manager.py`: conexión SQLite endurecida.

## Membresías

- FREE: calendario, resultados, live básico, favoritos básicos, picks limitados y SHARK básico.
- PRO: picks PRO, recomendaciones SHARK, riesgo/confianza/value básico, Telegram PRO y seguimiento.
- ELITE: SHARK completo, Auto Picks, combinadas automáticas, value avanzado, top picks y prioridad Telegram.

## V950/V951/V952

V950 organiza competiciones por país y separa los torneos internacionales en las
vistas de inicio, calendario y directorio.

V951 amplía la clasificación de competición con las estadísticas recibidas y
disponibles, reutiliza escudos de equipos solo cuando el nombre identifica una
única ficha en la competición y ofrece una vista móvil resumida que permite abrir
las estadísticas adicionales. Si una fuente no aporta una cifra, la interfaz la
marca como no disponible; no calcula ni presenta una clasificación inventada.

V952 añade al cliente la procedencia de la cronología del partido y la hora de la
última captura de eventos disponible. La hora se toma de las marcas guardadas en
los eventos; cuando no existe una marca válida, la pantalla lo indica sin usar el
reloj del partido o la hora actual como sustituto. No añade llamadas ni escrituras.

## Reglas de mantenimiento

- No crear apps paralelas.
- No duplicar proyecto.
- No inventar datos reales.
- No usar scraping ilegal.
- No convertir recomendaciones en picks publicados sin flujo admin.
- Mantener cliente limpio y admin separado.

## Siguiente paso

Mantener una versión acotada por cambio, con pruebas de regresión antes de integrar
en `main`. Una versión local no se considera publicada hasta comprobar el SHA y el
despliegue real de producción.
