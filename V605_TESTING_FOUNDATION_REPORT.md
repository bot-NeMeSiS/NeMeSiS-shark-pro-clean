# V605 — Testing Foundation & Smoke Checks

## Objetivo

Añadir una base de pruebas segura para detectar errores antes de subir a Render:

- errores de sintaxis
- imports rotos
- plantillas faltantes
- rutas duplicadas
- endpoints críticos caídos
- regresiones de seguridad básicas

Esta actualización no cambia la lógica de negocio de la app. Solo añade herramientas de validación.

## Archivos añadidos

- `tests/test_app_imports.py`
- `tests/test_templates_integrity.py`
- `tests/test_routes_smoke.py`
- `tests/test_security_baseline.py`
- `tools/smoke_check.py`
- `requirements-dev.txt`
- `pytest.ini`
- `.github/workflows/nemesis-smoke.yml`

## Cómo usarlo en local

Desde la carpeta raíz del proyecto:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
python tools/smoke_check.py
pytest
```

## Qué valida

### Smoke check rápido

```bash
python tools/smoke_check.py
```

Valida:

- compilación de `app.py`, `database_manager.py` y `engines/`
- importación de la app
- rutas duplicadas
- templates referenciados que no existan
- presencia de endpoints críticos

### Pytest

```bash
pytest
```

Valida:

- importación de app en modo test
- rutas básicas (`/`, `/live`, `/picks`, `/api/health` si existe)
- templates usados por `render_template()`
- baseline de seguridad para `SECRET_KEY`

## Importante

Si el test de seguridad falla porque existe fallback inseguro de `SECRET_KEY`, hay que aplicar o revisar V604.

## Resultado esperado

Antes de subir a Render, ejecutar:

```bash
python tools/smoke_check.py
pytest
```

Si ambas pruebas pasan, reduces mucho el riesgo de pantalla negra, rutas rotas o errores silenciosos.
