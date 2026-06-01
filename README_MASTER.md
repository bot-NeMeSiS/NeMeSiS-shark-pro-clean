# NeMeSiS SHARK PRO — README Master

## Estado

Versión actual: V600 Clean Core + V601 Live Intelligence.

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

## V600/V601

V600 consolida core y documentación sin rehacer el proyecto.

V601 introduce Live Intelligence:

- Momentum local/visitante.
- Presión.
- Dominancia.
- Riesgo.
- Timeline preparado para eventos.
- Alertas SHARK listas para Telegram.

## Reglas de mantenimiento

- No crear apps paralelas.
- No duplicar proyecto.
- No inventar datos reales.
- No usar scraping ilegal.
- No convertir recomendaciones en picks publicados sin flujo admin.
- Mantener cliente limpio y admin separado.

## Próximos pasos

Ver `V600_AUDIT_REPORT.md` para riesgos y roadmap V601-V605.
